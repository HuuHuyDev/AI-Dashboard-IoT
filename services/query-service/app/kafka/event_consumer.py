"""Kafka event consumer (CQRS updater).

The project expects an `event_consumer` object with `start()` and `stop()`.
In this repo state, the CQRS updater is optional for the Query Service's core
responsibility (execute SQL queries + caching). We provide a lightweight
implementation that keeps the service running even if Kafka consumption isn't
configured.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any


logger = logging.getLogger(__name__)


class EventConsumer:
	def __init__(self) -> None:
		self._stop_event: asyncio.Event | None = None

	async def start(self, read_model_service: Any) -> None:
		"""Start the consumer loop.

		This is intentionally a no-op loop that can be cancelled/stopped.
		"""
		if self._stop_event is None:
			self._stop_event = asyncio.Event()
		else:
			self._stop_event.clear()

		logger.info("Event consumer started (stub)")
		try:
			while not self._stop_event.is_set():
				await asyncio.sleep(5)
		except asyncio.CancelledError:
			raise
		finally:
			logger.info("Event consumer stopped (stub)")

	def stop(self) -> None:
		"""Signal the consumer loop to stop."""
		if self._stop_event is not None:
			self._stop_event.set()


event_consumer = EventConsumer()

