import asyncio
import logging
from typing import AsyncGenerator, Awaitable, Callable, List, Optional, Tuple, TypeVar

logger = logging.getLogger("promptforge.core.concurrent_runner")

T = TypeVar("T")

async def run_concurrent_sessions(
    tasks: List[Callable[[], Awaitable[T]]],
    concurrency: int = 8,
    on_result: Optional[Callable[[int, T], None]] = None,
) -> AsyncGenerator[Tuple[int, T], None]:
    """
    Executes N asynchronous task factories concurrently, capped at `concurrency` parallel tasks.
    Yields (task_index, result) as each individual task finishes (out-of-order streaming).
    """
    semaphore = asyncio.Semaphore(concurrency)
    queue: asyncio.Queue[Tuple[int, T]] = asyncio.Queue()

    async def worker(index: int, task_fn: Callable[[], Awaitable[T]]):
        async with semaphore:
            try:
                res = await task_fn()
                if on_result:
                    on_result(index, res)
                await queue.put((index, res))
            except Exception as e:
                logger.error(f"Concurrent task {index} encountered error: {e}", exc_info=True)
                raise

    # Launch all workers bounded by semaphore
    worker_tasks = [
        asyncio.create_task(worker(i, task_fn))
        for i, task_fn in enumerate(tasks)
    ]

    completed_count = 0
    total_tasks = len(tasks)

    while completed_count < total_tasks:
        item = await queue.get()
        completed_count += 1
        yield item

    await asyncio.gather(*worker_tasks)

async def run_concurrent_batch(
    tasks: List[Callable[[], Awaitable[T]]],
    concurrency: int = 8
) -> List[Tuple[int, T]]:
    """
    Executes tasks concurrently and returns a list of results as they finish.
    """
    results: List[Tuple[int, T]] = []
    async for item in run_concurrent_sessions(tasks, concurrency=concurrency):
        results.append(item)
    return results
