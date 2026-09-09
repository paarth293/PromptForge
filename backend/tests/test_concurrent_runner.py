import asyncio

import pytest

from backend.app.core.concurrent_runner import run_concurrent_batch, run_concurrent_sessions


@pytest.mark.asyncio
async def test_run_concurrent_sessions_streaming():
    # 20 tasks with varying tiny delays
    completed_order = []

    async def make_task(i: int):
        await asyncio.sleep(0.01 * (20 - i))  # Inverted delay to ensure out-of-order completion
        return f"result-{i}"

    tasks = [lambda i=i: make_task(i) for i in range(20)]

    streamed_results = []
    async for idx, res in run_concurrent_sessions(tasks, concurrency=8):
        streamed_results.append((idx, res))
        completed_order.append(idx)

    assert len(streamed_results) == 20
    # Confirm results did not come in strict 0..19 order because of async streaming
    assert completed_order != list(range(20))
    # All 20 task results present
    returned_indices = {item[0] for item in streamed_results}
    assert returned_indices == set(range(20))

@pytest.mark.asyncio
async def test_run_concurrent_batch():
    async def sample_task(i: int):
        await asyncio.sleep(0.005)
        return i * 2

    tasks = [lambda i=i: sample_task(i) for i in range(10)]
    batch_results = await run_concurrent_batch(tasks, concurrency=5)
    assert len(batch_results) == 10
    result_values = {res for _, res in batch_results}
    assert result_values == {i * 2 for i in range(10)}
