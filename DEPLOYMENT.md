# NewsRadar deployment environments

## Environments

| Environment | Git branch | Worker | Address | Trigger |
| --- | --- | --- | --- | --- |
| Production | `main` | `newsradar` | `https://newsradar.ccwu.cc` | Hourly content updates and approved promotions |
| Preview | `staging` | `newsradar-preview` | `https://preview.newsradar.ccwu.cc` | Local preview deployment |

The production checkout runs the hourly collector and keeps public news current.
Feature development belongs on `staging`; it must not be pushed directly to
`main`. The preview bundle is generated in `.deploy/preview`, receives a visible
preview badge, and sends `noindex` headers without changing production files.

## Preview deployment

From the staging checkout:

```sh
scripts/deploy_preview.sh
```

This refreshes `docs` without committing it, prepares an isolated bundle, and
deploys with `wrangler deploy --env preview`.

## Production promotion

Only run this after the owner explicitly approves the exact preview version:

```sh
scripts/promote_production.sh --approved
```

The command refuses dirty trees, non-staging branches, and a staging branch
that does not contain the latest `origin/main`. It runs release checks and then
pushes the exact staging commit to `main`. Cloudflare's production build remains
the production deploy mechanism.

## Cloudflare Access

`preview.newsradar.ccwu.cc` is protected by HTTP Basic authentication in the
preview-only Worker. The password is stored as the `PREVIEW_PASSWORD`
Cloudflare secret and in the local, mode-600 `.preview-auth.local` file. The
preview bundle also publishes `X-Robots-Tag: noindex, nofollow, noarchive` and
a restrictive `robots.txt`.

## Rollback

Use the Cloudflare Workers deployment history to roll back the Worker version.
Git remains the source of truth: restore or revert the corresponding commit on
`main`, then allow the production build to deploy it.
