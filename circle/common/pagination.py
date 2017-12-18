from rest_framework.pagination import PageNumberPagination, _positive_int
from rest_framework.utils.urls import remove_query_param, replace_query_param


class RelativePageNumberPagination(PageNumberPagination):
    page_size_query_param = 'page_size'

    def get_next_link(self):
        if not self.page.has_next():
            return None
        url = self.request.path
        page_number = self.page.next_page_number()
        return replace_query_param(url, self.page_query_param, page_number)

    def get_previous_link(self):
        if not self.page.has_previous():
            return None
        url = self.request.path
        page_number = self.page.previous_page_number()
        if page_number == 1:
            return remove_query_param(url, self.page_query_param)
        return replace_query_param(url, self.page_query_param, page_number)

    def get_page_size(self, request):
        if self.page_size_query_param:
            try:
                return _positive_int(
                    request.query_params[self.page_size_query_param],
                    strict=True,
                    cutoff=self.max_page_size
                )
            except (KeyError, ValueError):
                pass

        return None
