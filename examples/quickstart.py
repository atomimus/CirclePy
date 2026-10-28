"""Run all six clients offline, or explicitly opt into sandbox reads.

Run from a checkout or sdist: python -m examples.quickstart --offline
Real Circle calls require --sandbox --live and the dedicated sandbox config.
"""

import argparse
import asyncio
import json

from circlepy import (
    AdminV2Client, AsyncAdminV2Client, AsyncCircleClient,
    AsyncHeadlessClient, CircleClient, HeadlessClient,
)


def sync_reads(v1_key, v2_key, auth_key, community_id, member_id, *, origin="https://app.circle.so",
               expected_name=None):
    """Return full responses; only revoke the access token minted by this example."""
    options = dict(timeout=30, max_retries=0, raise_on_error=True, trust_env=False)
    with CircleClient(v1_key, community_id, base_url=origin+"/api/v1", **options) as legacy:
        v1 = legacy.community.get(community_id)
    with AdminV2Client(v2_key, base_url=origin+"/api/admin/v2", **options) as admin:
        v2 = admin.communities.get()
    _check_communities(v1, v2, community_id, expected_name)
    with HeadlessClient.create(auth_key, community_member_id=member_id,
                               community_url=origin, **options) as member:
        try:
            _check_identity(member.auth.to_tokens(), community_id, member_id)
            home = member.home.list_home_posts(page=1, per_page=2)
        finally:
            # A refresh token may be shared by other sessions. Leave it intact.
            member.auth.revoke_access_token()
    return {"admin_v1": v1, "admin_v2": v2, "headless": home}


async def async_reads(v1_key, v2_key, auth_key, community_id, member_id, *,
                      origin="https://app.circle.so", expected_name=None):
    """Use native async clients on the caller's event loop."""
    options = dict(timeout=30, max_retries=0, raise_on_error=True, trust_env=False)
    async with AsyncCircleClient(v1_key, community_id, base_url=origin+"/api/v1", **options) as legacy:
        v1 = await legacy.community.get(community_id)
    async with AsyncAdminV2Client(v2_key, base_url=origin+"/api/admin/v2", **options) as admin:
        v2 = await admin.communities.get()
    _check_communities(v1, v2, community_id, expected_name)
    async with await AsyncHeadlessClient.create(auth_key, community_member_id=member_id,
                                                community_url=origin, **options) as member:
        try:
            _check_identity(member.auth.to_tokens(), community_id, member_id)
            home = await member.home.list_home_posts(page=1, per_page=2)
        finally:
            await member.auth.revoke_access_token()
    return {"admin_v1": v1, "admin_v2": v2, "headless": home}


def _check_communities(v1, v2, community_id, name):
    if any(not isinstance(value, dict) or value.get("id") != community_id
           or (name is not None and value.get("name") != name) for value in (v1, v2)):
        raise ValueError("Quickstart community identity mismatch")


def _check_identity(tokens, community_id, member_id):
    if tokens.get("community_id") != community_id or tokens.get("community_member_id") != member_id:
        raise ValueError("Quickstart member identity mismatch")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--offline", action="store_true")
    group.add_argument("--sandbox", action="store_true")
    parser.add_argument("--live", action="store_true", help="Explicitly authorize configured sandbox reads and token lifecycle")
    parser.add_argument("--mode", choices=("sync", "async", "both"), default="both")
    args = parser.parse_args(argv)
    if args.offline and args.live:
        parser.error("--live is valid only with --sandbox")
    if args.sandbox and not args.live:
        parser.error("Sandbox I/O requires --sandbox --live")

    def run(keys, origin, name):
        results = []
        if args.mode in ("sync", "both"):
            results.append(sync_reads(*keys, origin=origin, expected_name=name))
        if args.mode in ("async", "both"):
            results.append(asyncio.run(async_reads(*keys, origin=origin, expected_name=name)))
        return results

    if args.offline:
        from .offline import community
        with community() as (origin, calls):
            results = run(("example-v1", "example-v2", "example-auth", 1, 2), origin, "Offline community")
        if any(result != results[0] for result in results):
            raise ValueError("Synthetic sync/async responses differ")
        print(json.dumps({"evidence": "synthetic_loopback", "modes": args.mode, "requests": len(calls)}))
    else:
        # Reuse the dedicated runner's explicit account/configuration and main
        # binding checks. No environment discovery or production fallback.
        from tools.sandbox import Config, verified_version
        config = Config.load()
        verified_version(config)
        run((config["ADMIN_V1_TOKEN"], config["ADMIN_V2_TOKEN"], config["HEADLESS_TOKEN"],
             config.number("COMMUNITY_ID"), config.number("MEMBER_ID")),
            config["ORIGIN"], config["COMMUNITY_NAME"])
        print(json.dumps({"evidence": "sandbox_quickstart", "modes": args.mode}))


if __name__ == "__main__":
    main()
