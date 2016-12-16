from nameko.web.handlers import http


class ProductsService:
    name = "products"

    @http("GET", "/products")
    def get_products(self, request):
        return 'ok'
