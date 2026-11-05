import asyncio

from app.api.v1.generation import with_keepalive


async def test_keepalive_emitted_while_source_is_quiet_and_events_pass_through():
    closed = []

    async def slow_source():
        try:
            yield "data: one\n\n"
            await asyncio.sleep(0.12)
            yield "data: two\n\n"
        finally:
            closed.append(True)

    out = [chunk async for chunk in with_keepalive(slow_source(), interval=0.03)]
    assert out[0] == "data: one\n\n"
    assert out[-1] == "data: two\n\n"
    assert ": keepalive\n\n" in out
    assert closed == [True]


async def test_closing_the_wrapper_closes_the_source():
    closed = []

    async def endless():
        try:
            while True:
                yield "data: tick\n\n"
                await asyncio.sleep(0.01)
        finally:
            closed.append(True)

    wrapper = with_keepalive(endless(), interval=0.05)
    await wrapper.__anext__()
    await wrapper.aclose()
    assert closed == [True]
