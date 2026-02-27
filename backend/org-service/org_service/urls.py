from django.urls import path
from django.views.decorators.csrf import csrf_exempt
from graphene_django.views import GraphQLView
from org_app.schema import schema


class HeaderGraphQLView(GraphQLView):
    def get_context(self, request):
        return request


urlpatterns = [
    path("graphql", csrf_exempt(HeaderGraphQLView.as_view(schema=schema, graphiql=False))),
]
