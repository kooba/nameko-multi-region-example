from marshmallow import Schema, fields


class Product(Schema):
    id = fields.Int(required=True)
    name = fields.String(required=True)
    price = fields.Decimal(as_string=True, required=True)
    quantity = fields.Int(required=True)


class Order(Schema):
    product_id = fields.Int(required=True)
    quantity = fields.Int(required=True)
