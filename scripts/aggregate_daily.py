"""
Aggregate daily statistics from logs table
Runs as a scheduled job to compute daily aggregations
"""
import logging
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
import sys
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database configuration
POSTGRES_HOST = os.getenv('POSTGRES_HOST', 'localhost')
POSTGRES_PORT = os.getenv('POSTGRES_PORT', '5432')
POSTGRES_DB = os.getenv('POSTGRES_DB', 'iot_dashboard')
POSTGRES_USER = os.getenv('POSTGRES_USER', 'iot_user')
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD', 'iot_password_2024')

DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"


def create_db_engine():
    """Create database engine"""
    try:
        engine = create_engine(DATABASE_URL, echo=False)
        logger.info("Database connection established")
        return engine
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        sys.exit(1)


def aggregate_daily_stats(engine, target_date):
    """
    Aggregate daily statistics for a specific date
    
    Args:
        engine: SQLAlchemy engine
        target_date: Date to aggregate (datetime.date)
    """
    try:
        with engine.connect() as conn:
            # Call the stored procedure
            sql = text("SELECT aggregate_daily_stats(:target_date)")
            conn.execute(sql, {"target_date": target_date})
            conn.commit()
            
            logger.info(f"Successfully aggregated stats for {target_date}")
            
    except Exception as e:
        logger.error(f"Error aggregating stats for {target_date}: {e}")
        raise


def aggregate_date_range(engine, start_date, end_date):
    """
    Aggregate daily statistics for a date range
    
    Args:
        engine: SQLAlchemy engine
        start_date: Start date
        end_date: End date
    """
    current_date = start_date
    success_count = 0
    error_count = 0
    
    while current_date <= end_date:
        try:
            aggregate_daily_stats(engine, current_date)
            success_count += 1
        except Exception as e:
            logger.error(f"Failed to aggregate {current_date}: {e}")
            error_count += 1
        
        current_date += timedelta(days=1)
    
    logger.info(f"Aggregation complete: {success_count} successful, {error_count} errors")


def get_missing_dates(engine):
    """
    Get dates that have logs but no daily_stats
    
    Args:
        engine: SQLAlchemy engine
        
    Returns:
        List of dates
    """
    try:
        with engine.connect() as conn:
            sql = text("""
                SELECT DISTINCT DATE(timestamp) as log_date
                FROM logs
                WHERE DATE(timestamp) NOT IN (
                    SELECT DISTINCT date FROM daily_stats
                )
                ORDER BY log_date
            """)
            
            result = conn.execute(sql)
            dates = [row[0] for row in result]
            
            logger.info(f"Found {len(dates)} dates with missing aggregations")
            return dates
            
    except Exception as e:
        logger.error(f"Error finding missing dates: {e}")
        return []


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Aggregate daily IoT statistics')
    parser.add_argument('--date', type=str, help='Specific date to aggregate (YYYY-MM-DD)')
    parser.add_argument('--yesterday', action='store_true', help='Aggregate yesterday\'s data')
    parser.add_argument('--today', action='store_true', help='Aggregate today\'s data')
    parser.add_argument('--days', type=int, help='Number of days back to aggregate')
    parser.add_argument('--missing', action='store_true', help='Aggregate all missing dates')
    parser.add_argument('--start-date', type=str, help='Start date for range (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str, help='End date for range (YYYY-MM-DD)')
    
    args = parser.parse_args()
    
    # Create database engine
    engine = create_db_engine()
    
    try:
        if args.date:
            # Aggregate specific date
            target_date = datetime.strptime(args.date, '%Y-%m-%d').date()
            logger.info(f"Aggregating data for {target_date}")
            aggregate_daily_stats(engine, target_date)
            
        elif args.yesterday:
            # Aggregate yesterday
            target_date = (datetime.now() - timedelta(days=1)).date()
            logger.info(f"Aggregating data for yesterday: {target_date}")
            aggregate_daily_stats(engine, target_date)
            
        elif args.today:
            # Aggregate today
            target_date = datetime.now().date()
            logger.info(f"Aggregating data for today: {target_date}")
            aggregate_daily_stats(engine, target_date)
            
        elif args.days:
            # Aggregate last N days
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=args.days)
            logger.info(f"Aggregating data from {start_date} to {end_date}")
            aggregate_date_range(engine, start_date, end_date)
            
        elif args.start_date and args.end_date:
            # Aggregate date range
            start_date = datetime.strptime(args.start_date, '%Y-%m-%d').date()
            end_date = datetime.strptime(args.end_date, '%Y-%m-%d').date()
            logger.info(f"Aggregating data from {start_date} to {end_date}")
            aggregate_date_range(engine, start_date, end_date)
            
        elif args.missing:
            # Aggregate all missing dates
            logger.info("Finding and aggregating missing dates")
            missing_dates = get_missing_dates(engine)
            
            if missing_dates:
                for date in missing_dates:
                    try:
                        aggregate_daily_stats(engine, date)
                    except Exception as e:
                        logger.error(f"Failed to aggregate {date}: {e}")
            else:
                logger.info("No missing dates found")
        else:
            # Default: aggregate yesterday
            target_date = (datetime.now() - timedelta(days=1)).date()
            logger.info(f"No arguments provided, aggregating yesterday: {target_date}")
            aggregate_daily_stats(engine, target_date)
            
    except Exception as e:
        logger.error(f"Aggregation failed: {e}", exc_info=True)
        sys.exit(1)
    finally:
        engine.dispose()
        logger.info("Database connection closed")


if __name__ == "__main__":
    main()
