# STAC Ingestion Test

This is a POC for a STAC Ingestion workflow that runs in GitHub actions with parallel compute power provided by [`coiled`](https://www.coiled.io/). The goal is to create the simplest possible process for ingesting STAC metadata for user-generated collections/assets.

The [`ingest` workflow](./.github/workflows/ingest.yml) authenticates with AWS and runs [`run.py`](./run.py) which reads a VEDA Dataset JSON document that specifies some details about the desired STAC collection and a few parameters that are used to find assets in S3. It uses [`rio-stac`](https://github.com/developmentseed/rio-stac) to create a STAC item.

It is not set up yet, but if the workflow were parameterized with `pgstac` database connection credentials, it would be able to post the resulting collections and items directly to the database.
