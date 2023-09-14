from marshmallow import Schema, fields
from flask import Flask, make_response
import sensorbucket
import geojson

baseurl = "http://10.0.0.245:5000"
app = Flask(__name__)


api = sensorbucket.ApiClient(sensorbucket.Configuration(
    host="https://sensorbucket.pollex.dev/api",
))

datastreams = [
    "0164d3d9-d2ad-4c87-896c-129c084f4d21",
    "97b35fcd-2baf-4e67-b00f-9b5417c45ad4",
    "0f40ebb3-c1e5-4f62-906a-5ffb8e97a920",
    "33fa454f-173e-4b95-9f85-c2259997cd6f",
    "cce4430f-3928-4f6b-a234-8f54f58ad799",
    "41b57f23-609d-4e95-b320-6f1c30b61d7d",
    "f5d119be-ed4f-4384-bdbe-ad4c97620cfc",
    "5e7cecb6-6320-4b70-82da-191269539efa",
    "16dc693b-977e-429a-b83e-cbb62c0a6b99",
    "b8ea3a74-1945-4380-a6c9-e7677c25b65f",
    "b51a9836-7b35-47f4-aaab-8933a10b8030",
    "96ebec07-4448-465c-a1a6-1870cc904d25",
    "ba06014d-999e-4ad4-8744-cb6bbeee0210",
    "269fa9f7-21c9-478f-8c2f-7608afc2b507",
    "903ce467-ccfb-4f86-93db-e936be984b6d",
    "afce796b-84b7-4588-a3b6-fe829ebc2cfa",
    "9927b020-2257-4d4e-ad06-45383cb72e0c",
    "5817f425-d6ed-4d66-a245-94ab900448eb",
    "2c358222-e9f1-48ca-b564-ef662ccd3a73",
    "74a28ef8-1ce8-486e-b921-76d6d596f4ae",
    "bf673305-e285-4fac-9ccd-8cea8bf068ab",
]


def respond(data, mt="application/json"):
    res = make_response(data)
    res.mimetype = mt
    return res


class Link:
    def __init__(self, path, rel, type="application/json"):
        self.href = path if path.startswith("http") else baseurl + path
        self.rel = rel
        self.type = type
        self.title = rel


class LinkSchema(Schema):
    href = fields.Str()
    rel = fields.Str()
    type = fields.Str()
    title = fields.Str()


class Landing:
    def __init__(self):
        self.title = "SensorBucket WFS"
        self.description = "Simple WFS implemented in Python to expose SensorBucket data"
        self.links = [
            Link("/", "self"),
            Link("/collections", "data"),
            Link("/conformance", "conformance"),
            Link("/api", "service-desc", "application/vnd.oai.openapi+json;version=3.0")
        ]


class LandingSchema(Schema):
    title = fields.Str()
    description = fields.Str()
    links = fields.List(fields.Nested(LinkSchema))


class Collection:
    def __init__(self, title, description):
        self.name = title.replace(' ', '_').lower()
        self.title = title
        self.description = description
        self.links = [
            Link(f"/collections/{self.name}/items", "item", "application/geo+json")
        ]


class CollectionSchema(Schema):
    name = fields.Str()
    title = fields.Str()
    description = fields.Str()
    links = fields.List(fields.Nested(LinkSchema))


class Collections:
    def __init__(self):
        self.collections = []
        self.links = [
            Link("/collections", "self", "application/json")
        ]

    def add(self, title, description):
        col = Collection(title, description)
        self.collections.append(col)
        self.links.append(Link(f"/collections/{col.name}", "item", "application/json"))

    def get(self, name):
        return next((item for item in self.collections if item.name == name), None)


class CollectionsSchema(Schema):
    links = fields.List(fields.Nested(LinkSchema))
    collections = fields.List(fields.Nested(CollectionSchema))


collections = Collections()
collections.add("Devices", "SensorBucket Devices")


@app.get("/")
def root():
    data = Landing()
    return respond(LandingSchema().dumps(data))


@app.get("/api")
def apiYaml():
    with open("api.yaml", "r") as file:
        contents = file.read()
    res = make_response(contents)
    res.mimetype = "application/vnd.oai.openapi+json;version=3.0"
    return res


@app.get("/collections")
def collectionsGet():
    return respond(CollectionsSchema().dumps(collections))


@app.get("/collections/<name>")
def collection(name):
    col = collections.get(name)
    return respond(CollectionSchema().dumps(col))


@app.get("/collections/<name>/items")
def getCollectionItems(name):
    M = sensorbucket.MeasurementsApi(api)
    features = []
    for id in datastreams:
        res = M.get_datastream(id)
        ds = res.data
        features.append(geojson.Feature(
            id=ds.device.code,
            geometry=geojson.Point((
                ds.device.longitude, ds.device.latitude
            )),
            properties={
                "description": ds.device.description,
                "sensor_desc": ds.sensor.description,
                "timestamp": ds.measurement_timestamp.isoformat(),
                "value": ds.measurement_value,
                "ds": id
            }
        ))
    fc = geojson.FeatureCollection(features)
    return respond(geojson.dumps(fc), "application/geo+json")
