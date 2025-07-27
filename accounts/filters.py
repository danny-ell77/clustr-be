import django_filters

from accounts.models import AccountUser


class AccountUserFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(method='filter_search')

    class Meta:
        model = AccountUser
        fields = []  # Add fields that you want to filter on here

    def filter_search(self, queryset, name, value):
        return queryset.filter(
            Q(email_address__icontains=value) |
            Q(first_name__icontains=value) |
            Q(last_name__icontains=value)
        )
