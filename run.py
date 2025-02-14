import json
import re
from datetime import datetime
from typing import List

import boto3
import coiled
from pypgstac.db import PgstacDB
from pypgstac.load import Loader, Methods
from pystac import Asset, Collection, Extent, Item, SpatialExtent, TemporalExtent
from pystac.extensions.render import Render, RenderExtension
from rio_stac import create_stac_item


def scan_s3_files(bucket: str, prefix: str, filename_regex: str) -> List[str]:
    """Scan S3 bucket for files matching the given regex pattern within specified prefix."""
    s3_client = boto3.client("s3")
    matching_files = []
    paginator = s3_client.get_paginator("list_objects_v2")

    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        if "Contents" not in page:
            continue

        # Check each object against the regex pattern
        for obj in page["Contents"]:
            key = obj["Key"]
            if re.match(
                filename_regex, key.split("/")[-1]
            ):  # Match against filename only
                matching_files.append(f"s3://{bucket}/{key}")

    return matching_files


@coiled.function(region="us-west-2", threads_per_worker=-1, local=True)
def _create_item(key: str, collection_id: str, asset_name: str) -> Item:
    return create_stac_item(
        source=key,
        collection=collection_id,
        asset_name=asset_name,
        with_proj=True,
    )


def load_into_pgstac(collection: str, items: str) -> None:
    db = PgstacDB()
    loader = Loader(db=db)

    loader.load_collections(
        collection,
        insert_mode=Methods.upsert,
    )

    loader.load_items(
        items,
        insert_mode=Methods.upsert,
    )


DATASET_JSON = "./icesat2-boreal-dataset.json"


def main():
    with open(DATASET_JSON) as f:
        dataset = json.load(f)

    collection = Collection(
        id=dataset["collection"],
        extent=Extent(
            spatial=SpatialExtent(bboxes=[*dataset["spatial_extent"].values()]),
            temporal=TemporalExtent(
                intervals=[
                    [
                        datetime.fromisoformat(dataset["temporal_extent"]["startdate"]),
                        datetime.fromisoformat(dataset["temporal_extent"]["enddate"]),
                    ]
                ]
            ),
        ),
        description=dataset["description"],
        assets={
            key: Asset.from_dict(asset_def)
            for key, asset_def in dataset["assets"].items()
        },
        stac_extensions=dataset["stac_extensions"],
    )

    collection.ext.add("render")
    RenderExtension.ext(collection).apply(
        {
            key: Render(render_params)
            for key, render_params in dataset["renders"].items()
        }
    )

    with open("/tmp/collection.json", "w") as f:
        f.write(json.dumps(collection.to_dict()))

    print("scanning for matching files in S3")
    inventory = []
    for discovery in dataset["discovery_items"]:
        inventory.extend(
            scan_s3_files(
                bucket=discovery["bucket"],
                prefix=discovery["prefix"],
                filename_regex=discovery["filename_regex"],
            )
        )

    print(f"found {len(inventory)} files")
    with open("/tmp/inventory.txt", "w") as f:
        for key in inventory:
            f.write(key + "\n")

    print("generating item metadata")
    asset_name = list(dataset["item_assets"].keys())[0]
    _items = _create_item.map(
        inventory[:10], collection_id=collection.id, asset_name=asset_name
    )

    count = 0
    with open("/tmp/items.ndjson", "w") as f:
        for item in _items:
            f.write(json.dumps(item.to_dict()) + "\n")
            count += 1

    print(f"wrote {count} items to ndjson")

    print("loading collection and items into pgstac database")
    load_into_pgstac(
        collection="/tmp/collection.json",
        items="/tmp/items.ndjson",
    )


if __name__ == "__main__":
    main()
