from rest_framework import pagination
from rest_framework.response import Response


class CustomPagination(pagination.PageNumberPagination):
    page_size = 10
    page_size_query_param = "per_page"
    max_page_size = 100
    page_query_param = "page"

    def get_paginated_response(self, data):
        return Response(
            {
                "next": self.get_next_link(),
                "previous": self.get_previous_link(),
                "current_page": self.page.number,
                "total_pages": self.page.paginator.num_pages,
                "data": data,
                "status" : 1,
                "message" : "success"
            }
        )
