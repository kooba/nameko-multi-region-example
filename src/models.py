from marshmallow import Schema, fields


class ProductBase(Schema):
    name = fields.String()
    price = fields.Decimal(as_string=True)


class Product(ProductBase):
    id = fields.Int(required=True)
