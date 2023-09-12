from marshmallow import Schema, fields
from flask import Flask, make_response
import sensorbucket
import geojson

baseurl = "http://10.0.0.245:5000"
app = Flask(__name__)


api = sensorbucket.ApiClient(sensorbucket.Configuration(
    host="http://127.0.0.1:3000/api"
))

datastreams = [
    "9b682284-850d-44f3-9ce2-d4451921bc61",
    "76ee346f-e2e1-4bcd-8d7a-68a270e889bd"
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
                "value": ds.measurement_value
            }
        ))
    fc = geojson.FeatureCollection(features)
    return respond(geojson.dumps(fc), "application/geo+json")
