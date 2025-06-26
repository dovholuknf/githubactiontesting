#!/usr/bin/env python3
import json, os, platform, shutil, stat, sys, tarfile, tempfile, urllib.request as url

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    
GITHUB_REPO_OWNER = os.getenv("GITHUB_REPO_OWNER", "openziti")
GITHUB_REPO_NAME  = os.getenv("GITHUB_REPO_NAME",  "ziti")
GITHUB_TOKEN      = os.getenv("GITHUB_TOKEN", "")

def _arch():
    m = platform.machine().lower()
    if m in ("x86_64", "amd64"):         return "amd64"
    if m in ("aarch64", "arm64"):        return "arm64"
    if m.startswith("arm"):              return "arm"
    raise RuntimeError(f"unsupported arch: {m}")

def _os():
    p = sys.platform
    if   p.startswith("linux"):   return "linux"
    elif p == "darwin":           return "darwin"
    elif p in ("win32", "cygwin"):return "windows"
    raise RuntimeError(f"unsupported os: {p}")

def _github_json(path):
    req = url.Request(f"https://api.github.com{path}")
    if GITHUB_TOKEN: req.add_header("Authorization", f"Bearer {GITHUB_TOKEN}")
    with url.urlopen(req) as r:
        return json.load(r)

def _latest_version():
    data = _github_json(f"/repos/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/releases/latest")
    return data["tag_name"], next(a["name"] for a in data["assets"]
                                  if a["name"].startswith(f"ziti-{_os()}-{_arch()}-"))

def _verify_version(vtag):
    try:
        data = _github_json(f"/repos/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/releases/tags/{vtag}")
        fname = next(a["name"] for a in data["assets"]
                     if a["name"].startswith(f"ziti-{_os()}-{_arch()}-"))
        return vtag, fname
    except Exception as e:
        raise RuntimeError(f"version {vtag} not found") from e

def get_ziti(add_to_path: bool = False) -> str:
    """Download & extract ziti; return path to binary, with progress output."""
    override = os.getenv("ZITI_VERSION_OVERRIDE")
    tag, tar_name = (_verify_version(override) if override else _latest_version())
    print(f"🔍 using tag={tag}  archive={tar_name}")

    zhome = os.getenv("ZITI_HOME", os.path.expanduser("~/.ziti"))
    zbin  = os.getenv("ZITI_BIN_DIR",
                      os.path.join(zhome, "ziti-bin", f"ziti-{tag}"))
    ziti_path = os.path.join(zbin, "ziti")

    # already present?
    if os.path.isfile(ziti_path):
        print(f"✅ existing ziti at {ziti_path}")
        if add_to_path and zbin not in os.getenv("PATH", ""):
            os.environ["PATH"] += os.pathsep + zbin
            print(f"➕ added {zbin} to PATH")
        return ziti_path

    print(f"📁 creating {zbin}")
    os.makedirs(zbin, exist_ok=True)

    url_file = (
        f"https://github.com/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}"
        f"/releases/download/{tag}/{tar_name}"
    )
    print(f"⬇️  downloading {url_file}")
    tmp = tempfile.NamedTemporaryFile(delete=False)
    try:
        with url.urlopen(url_file) as r, open(tmp.name, "wb") as f:
            shutil.copyfileobj(r, f)
        print("✔️  download complete")

        print("📦 extracting …")
        with tarfile.open(tmp.name) as t:
            member = next(
                m for m in t.getmembers()
                if m.name.endswith("/ziti") or m.name == "ziti"
            )
            t.extract(member, path=zbin if member.name == "ziti"
                      else os.path.join(zbin, "tmp"))
            if "/" in member.name:
                shutil.move(os.path.join(zbin, "tmp", member.name), ziti_path)
                shutil.rmtree(os.path.join(zbin, "tmp"))
        os.chmod(ziti_path, os.stat(ziti_path).st_mode | stat.S_IEXEC)
        print(f"✅ extracted to {ziti_path}")

        if add_to_path:
            os.environ["PATH"] += os.pathsep + zbin
            print(f"➕ added {zbin} to PATH")

        return ziti_path
    finally:
        os.unlink(tmp.name)


get_ziti(add_to_path=False)