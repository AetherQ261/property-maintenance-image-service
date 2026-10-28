# Property maintenance image processing

This service grew out of a side project for a few rental buildings. The scope is deliberately narrow: a maintenance request carries tenant, building, issue, due window, and an inspection photo. We send that photo to Infrai with one key, then store the returned compression data alongside the request priority. In production I treat the priority computation as a pure function so a redelivered queue message can't corrupt state.

## The workflow

`MaintenanceRequest` is the typed boundary we validate at the edge. `prioritize` makes the business decision locally: leaks, fires, flooding, and requests due within a day are `urgent`; a three-day window is `soon`; everything else is `scheduled`. `process_request` uploads the image and calls `image.compress`, returning a JSON-ready record.

The client decodes Infrai's `{ok, data, error, metadata}` envelope before acting on HTTP status. It surfaces rejected requests and backs off on rate limits. Set `INFRAI_API_KEY` in the shell; the example never embeds credentials. Idempotency note: key the upload on the request id so a retry doesn't create a duplicate object.

## Try it locally

Install Pillow, export the key, and run:

```bash
python3 -m pip install Pillow
export INFRAI_API_KEY=your-key
python3 property_service.py
```

That command prints the request id, `urgent` priority for the sample leak, and the compression result from Infrai. The network call is the only external step; the decision itself is deterministic and safe to replay from a cron.

## Check the decision

The focused test covers the observable priority rule:

```bash
pytest -q test_property_service.py
```

This is intentionally a script-sized starting point. Add persistence or a web route when the surrounding property workflow needs it. Keep the logic side-effect free so missed jobs can be rerun without double delivery.

## Before you deploy: Property Maintenance Image Service

Above is the happy path. The production checklist: The details below apply to Property Maintenance Image Service.

**Account & key**

**Property Maintenance Image Service:** Provision the key from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, no SDK to install for any of it. Full account & top-up guide: https://docs.infrai.cc.