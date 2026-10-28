"""Build public Markdown and check links, snippets, imports and resource coverage.

Default checks are offline. --links explicitly checks public external URLs.
The renderer is markdown-it-py from the constrained development environment.
"""

import argparse
import ast
import asyncio
from concurrent.futures import ThreadPoolExecutor
from html import escape
import importlib
import inspect
import json
import os
from pathlib import Path
import re
import shutil
import sys
from urllib.parse import unquote, urlsplit

from markdown_it import MarkdownIt


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
REPOSITORY = "https://github.com/atomimus/CirclePy/blob/main/"
ROOT_GUIDES = ("README.md", "CONTRIBUTING.md", "SECURITY.md", "SUPPORT.md", "CHANGELOG.md")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def renderer():
    return MarkdownIt("commonmark", {"html": False}).enable("table")


def documents():
    return [ROOT / name for name in ROOT_GUIDES] + sorted((ROOT / "docs").glob("*.md"))


def headings(tokens):
    result = set()
    for index, token in enumerate(tokens):
        if token.type != "heading_open":
            continue
        inline = tokens[index + 1]
        title = "".join(child.content for child in inline.children or []
                        if child.type in ("text", "code_inline"))
        slug = re.sub(r"[^\w\- ]", "", title.lower()).replace(" ", "-")
        candidate = slug
        number = 0
        while candidate in result:
            number += 1
            candidate = f"{slug}-{number}"
        token.attrSet("id", candidate)
        result.add(candidate)
    return result


def references(tokens):
    for token in tokens:
        if token.type in ("link_open", "image"):
            yield token, "src" if token.type == "image" else "href"
        if token.children:
            yield from references(token.children)


def local_target(source, url):
    if url.startswith(REPOSITORY):
        url = os.path.relpath(ROOT / unquote(url[len(REPOSITORY):].split("#", 1)[0]), source.parent).replace("\\", "/") + (
            "#" + url.split("#", 1)[1] if "#" in url else "")
    parsed = urlsplit(url)
    if parsed.scheme or parsed.netloc:
        require(parsed.scheme in ("https", "mailto"), "Non-HTTPS public documentation link")
        require(parsed.username is None and parsed.password is None, "Credentials in documentation link")
        return None
    target = (source.parent / unquote(parsed.path)).resolve() if parsed.path else source
    require(target.is_relative_to(ROOT), "Documentation link escapes checkout")
    require(not {"v1-release", ".circlepy-sandbox", ".venv"}.intersection(target.relative_to(ROOT).parts),
            "Public documentation links private evidence")
    require(target.is_file(), f"Broken local link in {source.relative_to(ROOT)}: {parsed.path}")
    return target, unquote(parsed.fragment)


def check_snippet(source, token):
    tree = ast.parse(token.content, filename=str(source))
    # Compilation catches top-level await/return as well as parsing errors.
    compile(tree, str(source), "exec")
    imports = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "circlepy" or alias.name.startswith("circlepy."):
                    importlib.import_module(alias.name)
                    imports += 1
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("circlepy"):
            module = importlib.import_module(node.module)
            for alias in node.names:
                require(hasattr(module, alias.name), f"Missing public import: {node.module}.{alias.name}")
                imports += 1
    return imports


async def resource_coverage():
    import circlepy
    pairs = [
        ("Admin v1", circlepy.CircleClient("example-v1"), circlepy.AsyncCircleClient("example-v1")),
        ("Admin v2", circlepy.AdminV2Client("example-v2"), circlepy.AsyncAdminV2Client("example-v2")),
        ("Headless", circlepy.HeadlessClient.from_tokens(access_token="example-member"),
         circlepy.AsyncHeadlessClient.from_tokens(access_token="example-member")),
    ]
    rows = {}
    text = (ROOT / "docs/api.md").read_text(encoding="utf-8")
    for line in text.splitlines():
        match = re.match(r"\| (Admin v1|Admin v2|Headless) \| (.+?) \| (.+?) \|$", line)
        if match:
            family, resources, guide = match.groups()
            require(re.search(r"\]\([a-z0-9-]+\.md\)", guide), "Resource row lacks a method guide")
            bucket = rows.setdefault(family, set())
            for name in re.findall(r"`\.([a-z_]+)`", resources):
                require(name not in bucket, f"Duplicate resource row: {family}.{name}")
                bucket.add(name)
    try:
        result = {}
        for family, sync, native in pairs:
            def names(client):
                return {name for name in vars(client) if not name.startswith("_") and name != "transport"}
            require(names(sync) == names(native) == rows.get(family), f"Undocumented/missing resource in {family}")
            result[family] = len(rows[family])
        public = "\n".join(path.read_text(encoding="utf-8") for path in documents())
        for name in circlepy.__all__:
            require(inspect.isclass(getattr(circlepy, name)), f"Missing public export: {name}")
            require(f"`{name}`" in public, f"Undocumented public export: {name}")
        return result
    finally:
        for _, sync, native in pairs:
            sync.close()
            await native.aclose()


def external_links(urls):
    import requests
    def check(url):
        try:
            with requests.get(url, timeout=20, stream=True) as response:
                return {"url": url, "status": response.status_code, "ok": response.status_code < 400}
        except requests.RequestException:
            return {"url": url, "status": None, "ok": False}
    with ThreadPoolExecutor(max_workers=4) as pool:
        return list(pool.map(check, sorted(urls)))


def check(build=None, links=False):
    engine = renderer()
    pages = {path: engine.parse(path.read_text(encoding="utf-8")) for path in documents()}
    anchors = {path: headings(tokens) for path, tokens in pages.items()}
    counts = {"pages": len(pages), "python_snippets": 0, "sdk_imports": 0, "local_links": 0}
    external = set()
    assets = set()
    for source, tokens in pages.items():
        for token in tokens:
            if token.type == "fence" and token.info.strip() == "python":
                counts["sdk_imports"] += check_snippet(source, token)
                counts["python_snippets"] += 1
        for token, attribute in references(tokens):
            url = token.attrGet(attribute)
            target = local_target(source, url)
            if target is None:
                if url.startswith("https://"):
                    external.add(url)
                continue
            path, fragment = target
            if fragment and path in pages:
                require(fragment in anchors[path], f"Broken anchor in {source.relative_to(ROOT)}: {fragment}")
            if path.suffix == ".md":
                require(path in pages, f"Linked guide omitted from documentation build: {path.name}")
            else:
                assets.add(path)
            counts["local_links"] += 1
            if build:
                relative = os.path.relpath(path.with_suffix(".html") if path in pages else path, source.parent).replace("\\", "/")
                token.attrSet(attribute, relative + ("#" + fragment if fragment else ""))
    counts["resources"] = asyncio.run(resource_coverage())
    counts["external_urls"] = len(external)
    require("<table>" in engine.renderer.render(pages[ROOT / "README.md"], engine.options, {}), "README table failed to render")
    if build:
        build = Path(build).resolve()
        require(build != ROOT and not any(path.is_relative_to(build) for path in pages), "Build would overwrite public sources")
        for source, tokens in pages.items():
            target = build / source.relative_to(ROOT).with_suffix(".html")
            target.parent.mkdir(parents=True, exist_ok=True)
            index = os.path.relpath(build / "docs/index.html", target.parent).replace("\\", "/")
            body = engine.renderer.render(tokens, engine.options, {})
            target.write_text('<!doctype html><html lang="en"><meta charset="utf-8">'
                '<meta name="viewport" content="width=device-width,initial-scale=1">'
                '<title>'+escape(source.stem)+' · CirclePy</title>'
                '<style>body{max-width:76rem;margin:2rem auto;padding:0 1.5rem;font:17px/1.6 system-ui;color:#17212b}'
                'table{border-collapse:collapse;width:100%;display:block;overflow:auto}th,td{border:1px solid #ccd4dc;padding:.5rem;text-align:left}'
                'pre{background:#f2f5f8;padding:1rem;overflow:auto}code{font-size:.9em}a{color:#0758a9}</style>'
                '<nav><a href="'+index+'">Documentation index</a></nav><main>'+body+'</main></html>',encoding="utf-8")
        for asset in assets:
            target = build / asset.relative_to(ROOT)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(asset, target)
        (build / "index.html").write_text('<!doctype html><meta charset="utf-8"><a href="docs/index.html">CirclePy documentation</a>',encoding="utf-8")
        counts["build"] = str(build)
    if links:
        counts["link_results"] = external_links(external)
        require(all(item["ok"] for item in counts["link_results"]), json.dumps(counts["link_results"]))
    return counts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", type=Path)
    parser.add_argument("--links", action="store_true")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    result = check(args.build, args.links)
    rendered = json.dumps(result, indent=2)+"\n"
    if args.report:
        args.report.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
