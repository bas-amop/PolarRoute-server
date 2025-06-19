# Vehicle Management

In order to add vehicles to environment meshes, they will first need to be created in the database.

For details on the API, see the [API reference page](api.md).

## Creating vehicles

To request a vehicle to be added to the database, make a POST request to the `/api/vehicle` endpoint,
for example with the following CURL:

```shell
curl --header "Content-Type: application/json" \
  --request POST \
  --data '{
    "vessel_type":"SDA",
    "max_speed":"26.5",
    "unit":"km/hr",
    "beam":"24.0"
    }' \
  http://localhost:8000/api/vehicle
```

This will create a vehicle of `vessel_type` "SDA" in the database. Note that `vessel_type` is unique,
and any subsequent request to create the same vessel type will result in an error.

## Updating vehicle properties

Should you wish to update a `vessel_type`'s properties after creation, you can do so using the
`force_properties` argument in your request.

Let's say we actually wanted to display the speed in knots:

```shell
curl --header "Content-Type: application/json" \
  --request POST \
  --data '{
    "vessel_type":"SDA",
    "max_speed":"14.31",
    "unit":"knots",
    "beam":"24.0",
    "force_properties":"true"
    }' \
  http://localhost:8000/api/vehicle
```
With `"force_properties"` set to `"true"`, the request will be accepted and the properties for "SDA"
will be updated.

## Requesting a vehicle

Coming soon.

## Requesting all vehicles

Coming soon.

## Adding a vehicle to an environment mesh

Coming soon.