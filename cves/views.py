from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.urls import reverse, reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from .filters import CVEFilter
from .forms import CVEForm
from .models import CVE


class CVEPermissionRequiredMixin(PermissionRequiredMixin):
    login_url = reverse_lazy("admin:login")


class CVEListView(ListView):
    model = CVE
    template_name = "cves/list.html"
    context_object_name = "cves"
    paginate_by = 50

    def get_queryset(self):
        self.filterset = CVEFilter(self.request.GET, queryset=CVE.objects.all())
        return self.filterset.qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query_params = self.request.GET.copy()
        query_params.pop("page", None)
        context["filterset"] = self.filterset
        context["query_string"] = query_params.urlencode()
        context["api_list_url"] = reverse("cve-list")
        return context


class CVEDetailView(DetailView):
    model = CVE
    template_name = "cves/detail.html"
    context_object_name = "cve"
    slug_field = "cve_id"
    slug_url_kwarg = "cve_id"


class CVECreateView(CVEPermissionRequiredMixin, CreateView):
    model = CVE
    form_class = CVEForm
    template_name = "cves/form.html"
    permission_required = "cves.add_cve"

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"{self.object.cve_id} was created.")
        return response

    def get_success_url(self):
        return reverse("cves:detail", kwargs={"cve_id": self.object.cve_id})


class CVEUpdateView(CVEPermissionRequiredMixin, UpdateView):
    model = CVE
    form_class = CVEForm
    template_name = "cves/form.html"
    context_object_name = "cve"
    slug_field = "cve_id"
    slug_url_kwarg = "cve_id"
    permission_required = "cves.change_cve"

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"{self.object.cve_id} was updated.")
        return response

    def get_success_url(self):
        return reverse("cves:detail", kwargs={"cve_id": self.object.cve_id})


class CVEDeleteView(CVEPermissionRequiredMixin, DeleteView):
    model = CVE
    template_name = "cves/confirm_delete.html"
    context_object_name = "cve"
    slug_field = "cve_id"
    slug_url_kwarg = "cve_id"
    permission_required = "cves.delete_cve"
    success_url = reverse_lazy("cves:list")

    def form_valid(self, form):
        cve_id = self.object.cve_id
        response = super().form_valid(form)
        messages.success(self.request, f"{cve_id} was deleted.")
        return response
