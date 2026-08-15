"""npm registry fetching with on-disk caching and package-level closure discovery."""

import concurrent.futures
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

REGISTRY = "https://registry.npmjs.org"
CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "registry")

SEED = [
    "express", "react", "react-dom", "lodash", "axios", "next", "vue", "typescript",
    "jest", "eslint", "webpack", "moment", "request", "node-fetch", "async",
    "chalk", "commander", "debug", "dotenv", "uuid", "jsonwebtoken", "body-parser",
    "cookie-parser", "helmet", "cors", "mongoose", "pg", "sequelize", "graphql",
    "apollo-server-express", "socket.io", "bcryptjs", "yargs", "rxjs", "inquirer",
    "class-validator", "aws-sdk", "google-auth-library", "openai", "zod", "crypto-js",
    "fastify", "hapi", "koa", "express-session", "multer", "passport", "passport-jwt",
    "ioredis", "redis", "amqplib", "kafkajs", "bull", "winston", "pino", "morgan",
    "compression", "superagent", "got", "undici", "form-data", "mime-types", "cookie",
    "fresh", "etag", "statuses", "content-type", "vary", "range-parser", "proxy-addr",
    "forwarded", "ipaddr.js", "encodeurl", "parseurl", "path-to-regexp", "serve-static",
    "finalhandler", "send", "accepts", "negotiator", "bytes", "qs", "side-channel",
    "function-bind", "has-symbols", "es-errors", "call-bind", "get-intrinsic",
    "object-inspect", "safe-buffer", "isarray", "inherits", "util-deprecate",
    "string_decoder", "readable-stream", "process-nextick-args", "core-util-is", "ms",
    "semver", "supports-color", "has-flag", "color-convert", "color-name", "ansi-styles",
    "ansi-regex", "strip-ansi", "string-width", "emoji-regex", "wrap-ansi", "cliui",
    "y18n", "yargs-parser", "find-up", "locate-path", "p-locate", "p-limit", "p-try",
    "path-exists", "resolve", "resolve-from", "import-fresh", "parent-module",
    "callsites", "is-glob", "is-extglob", "is-number", "fill-range", "micromatch",
    "braces", "picomatch", "to-regex-range", "anymatch", "binary-extensions",
    "chokidar", "glob", "glob-parent", "minimatch", "brace-expansion", "graceful-fs",
    "rimraf", "mkdirp", "minimist", "camelcase", "decamelize", "require-directory",
    "nanoid", "js-cookie", "react-router", "react-router-dom", "redux", "react-redux",
    "zustand", "mobx", "formik", "yup", "framer-motion", "styled-components",
    "tailwindcss", "autoprefixer", "postcss", "sass", "less", "babel-loader",
    "ts-loader", "esbuild", "vite", "rollup", "prettier", "stylelint", "husky",
    "lint-staged", "nodemon", "concurrently", "cross-env", "dotenv-expand", "env-cmd",
    "pkg", "electron", "prisma", "drizzle-orm", "typeorm", "knex", "better-sqlite3",
    "sqlite3", "mysql2", "mongodb", "firebase-admin", "stripe", "twilio", "sendgrid",
    "nodemailer", "pdfkit", "xlsx", "papaparse", "dayjs", "date-fns", "luxon",
    "validator", "sanitize-html", "dompurify", "marked", "highlight.js", "sharp",
    "canvas", "puppeteer", "playwright", "cheerio", "jsdom", "mocha", "chai",
    "vitest", "c8", "nyc", "ts-node", "ts-jest", "eslint-plugin-react",
    "eslint-plugin-import", "eslint-config-airbnb",
]


def _cache_path(name):
    return os.path.join(CACHE_DIR, urllib.parse.quote(name, safe="") + ".json")


def fetch(name):
    """Fetch a package doc from the registry, caching to disk."""
    path = _cache_path(name)
    if os.path.exists(path):
        try:
            with open(path) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            os.remove(path)  # corrupt/truncated cache; refetch
    url = f"{REGISTRY}/{urllib.parse.quote(name, safe='')}"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                doc = json.loads(resp.read().decode())
            os.makedirs(CACHE_DIR, exist_ok=True)
            with open(path, "w") as f:
                json.dump(doc, f)
            return doc
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if e.code == 429:
                time.sleep(2 * (attempt + 1))
                continue
            raise
        except (urllib.error.URLError, TimeoutError):
            time.sleep(1 * (attempt + 1))
    return None


def declared_dep_names(doc):
    """All dependency names declared by any version of a package."""
    names = set()
    if not doc:
        return names
    for ver in doc.get("versions", {}).values():
        for field in ("dependencies", "optionalDependencies"):
            names.update(ver.get(field, {}).keys())
    return names


def collect_closure(seed, max_packages, max_depth=4, workers=12):
    """BFS from seed over declared dependency names. Returns dict name->doc."""
    docs = {}
    frontier = [s for s in seed if s and s[0] not in "@"]
    depth = 0
    while frontier and len(docs) < max_packages and depth < max_depth:
        batch = frontier[: max_packages - len(docs)]
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
            results = list(ex.map(fetch, batch))
        for name, doc in zip(batch, results):
            if doc is not None:
                docs[name] = doc
        next_frontier = set()
        for doc in docs.values():
            next_frontier.update(declared_dep_names(doc))
        next_frontier -= set(docs.keys())
        next_frontier -= {"npm", "typescript"}  # huge meta packages
        next_frontier = {n for n in next_frontier if n and n[0] not in "@"}
        frontier = sorted(next_frontier)
        depth += 1
        print(f"[closure] depth {depth}: {len(docs)} packages cached, frontier {len(frontier)}")
    return docs
