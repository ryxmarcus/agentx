"""
Persistent Browser Daemon 2 (Windows-compatible)
Secondary worker connecting to Playwright CDP.
Accepts commands via stdin, prints single-line JSON on stdout.
"""
import asyncio
import json
import sys
import threading
import queue
from playwright.async_api import async_playwright

cmd_queue = queue.Queue()

def stdin_reader():
    for line in sys.stdin:
        line = line.strip()
        if line:
            cmd_queue.put(line)
    cmd_queue.put(None)

async def handle(cmd_str, context):
    try:
        cmd = json.loads(cmd_str)
    except json.JSONDecodeError as e:
        return {"error": f"Bad JSON: {e}"}

    action = cmd.get("cmd", "")
    page_idx = cmd.get("page", None)

    try:
        if action == "ping":
            return {"ok": True, "worker": 2, "pages": len(context.pages)}

        if action == "pages":
            out = []
            for i, p in enumerate(context.pages):
                out.append({"i": i, "url": p.url, "title": await p.title()})
            return {"pages": out, "worker": 2}

        if action == "new_tab":
            url = cmd.get("url", "about:blank")
            p = await context.new_page()
            if url != "about:blank":
                await p.goto(url, wait_until="domcontentloaded", timeout=15000)
            return {"ok": True, "new_page_index": len(context.pages) - 1, "url": p.url}

        if page_idx is None:
            for i, p in enumerate(context.pages):
                if 'intellihub' not in p.url.lower() and 'allcargo' not in p.url.lower():
                    page_idx = i
                    break
            if page_idx is None:
                page_idx = 0

        pages = context.pages
        if page_idx >= len(pages):
            return {"error": f"Page {page_idx} not found, have {len(pages)}"}
        page = pages[page_idx]

        if action == "eval":
            js = cmd.get("js", "")
            args = cmd.get("args", None)
            r = await page.evaluate(js, args) if args is not None else await page.evaluate(js)
            return {"r": r}

        elif action == "click":
            await page.click(cmd["selector"])
            return {"ok": True}

        elif action == "fill":
            await page.fill(cmd["selector"], cmd["text"])
            return {"ok": True}

        elif action == "type":
            await page.type(cmd["selector"], cmd["text"], delay=cmd.get("delay", 0))
            return {"ok": True}

        elif action == "text":
            t = await page.inner_text(cmd.get("selector", "body"))
            mx = cmd.get("max", 4000)
            if len(t) > mx:
                t = t[:mx] + f"\n...[{len(t)} chars total]"
            return {"t": t}

        elif action == "html":
            el = await page.query_selector(cmd.get("selector", "body"))
            if not el:
                return {"error": "not found"}
            h = await el.evaluate("e => e.outerHTML")
            mx = cmd.get("max", 4000)
            if len(h) > mx:
                h = h[:mx] + "...[truncated]"
            return {"h": h}

        elif action == "wait":
            await page.wait_for_timeout(cmd.get("ms", 500))
            return {"ok": True}

        elif action == "screenshot":
            path = cmd.get("path", "C:/Users/rah_66160/iTopaz-agents/screenshot_daemon2.png")
            await page.screenshot(path=path)
            return {"ok": True, "path": path}

        elif action == "navigate":
            await page.goto(cmd["url"], wait_until="domcontentloaded", timeout=15000)
            return {"ok": True, "url": page.url}

        elif action == "check":
            await page.check(cmd["selector"])
            return {"ok": True}

        elif action == "uncheck":
            await page.uncheck(cmd["selector"])
            return {"ok": True}

        elif action == "upload":
            await page.set_input_files(cmd["selector"], cmd["files"])
            return {"ok": True}

        else:
            return {"error": f"Unknown: {action}"}

    except Exception as e:
        return {"error": str(e)}

async def main():
    t = threading.Thread(target=stdin_reader, daemon=True)
    t.start()

    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp('http://127.0.0.1:9222')
        ctx = browser.contexts[0]
        print(json.dumps({"ready": True, "worker": 2, "pages": len(ctx.pages)}), flush=True)

        while True:
            try:
                line = cmd_queue.get_nowait()
            except queue.Empty:
                await asyncio.sleep(0.05)
                continue

            if line is None:
                break

            result = await handle(line, ctx)
            print(json.dumps(result), flush=True)

asyncio.run(main())

