from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, Http404, JsonResponse
from django.views import generic
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.core.urlresolvers import reverse_lazy
from django.db.models import Q
from django.contrib import messages

from profiles.models import FacultyDetail, StudentDetail
from .models import Notice, BookmarkedNotice
from .forms import NoticeCreateForm
import utils.constants as constants

from datetime import datetime
from braces.views import LoginRequiredMixin, GroupRequiredMixin

class NoticeList(LoginRequiredMixin, generic.View):

    def get(self, request):
        category = request.GET.get('category', None)
        template = 'notices/list.html'
        search = request.GET.get('search', None)

        page_type = ''
        if category is None:
            notice_list = Notice.objects.order_by('-modified')
            page_type = 'All Notices'
        else:
            notice_list = Notice.objects.filter(category=category).order_by('-modified')
            page_type = category

        if search is not None:
            notice_list = Notice.objects.filter(Q(faculty__user__username__contains=search) |
                Q(faculty__user__first_name__contains=search) |
                Q(faculty__user__last_name__contains=search) |
                Q(category__contains=search) |
                Q(title__contains=search) |
                Q(description__contains=search) |
                Q(category__contains=search) |
                Q(course_branch_year__contains=search))
            notice_list = notice_list.order_by('-modified')

        bookmark_id_list = BookmarkedNotice.objects.filter(user=request.user).values_list('notice__pk', flat=True)

        # To check if the notices are bookmarked by user or not
        for notice in notice_list:
            for bookmark_id in bookmark_id_list:
                if bookmark_id == notice.pk:
                    notice.is_bookmarked_by_user = True
                    break
                else:
                    notice.is_bookmarked_by_user = False

        paginator = Paginator(notice_list, constants.NOTICES_TO_DISPLAY_ON_SINGLE_PAGE)
        page = request.GET.get('page')
        try:
            notices = paginator.page(page)
        except PageNotAnInteger:
            # If page is not an integer, deliver first page.
            notices = paginator.page(1)
        except EmptyPage:
            # If page is out of range (e.g. 9999), deliver last page of results.
            notices = paginator.page(paginator.num_pages)
        return render(request, template, {"notices": notices, 'page_type':page_type})

# class FullTextSearch(LoginRequiredMixin, generic.View):
#     def get(self, request):
#         template = 'notices/list.html'
#         page_type = 'All Notices'

#         text = request.GET.get('search', '')
#         category = request.GET.get('category', '')

#         notices = Notice.objects.all()
#         notices = notices.filter(Q(faculty__user__username__contains=text) |
#                 Q(faculty__user__first_name__contains=text) |
#                 Q(faculty__user__last_name__contains=text) |
#                 Q(category__contains=text) |
#                 Q(title__contains=text) |
#                 Q(description__contains=text) |
#                 Q(category__contains=text) |
#                 Q(course_branch_year__contains=text))

#         paginator = Paginator(notices, constants.NOTICES_TO_DISPLAY_ON_SINGLE_PAGE)
        
#         page = request.GET.get('page','')
#         page = page+'?search='+'text'+'category='+category
        
#         try:
#             notices = paginator.page(page)
#         except PageNotAnInteger:
#             # If page is not an integer, deliver first page.
#             notices = paginator.page(1)
#         except EmptyPage:
#             # If page is out of range (e.g. 9999), deliver last page of results.
#             notices = paginator.page(paginator.num_pages)
#         return render(request, template, {"notices": notices, 'page_type':page_type, 
#             'search':text, 'category':category})

class CreateNotice(LoginRequiredMixin, GroupRequiredMixin, CreateView):
    """
    View for creating the Notices
    """
    group_required = u'FacultyGroup'
    form_class = NoticeCreateForm
    exclude = ['faculty']
    success_url = reverse_lazy('notice-list')
    template_name = "notices/notice_create.html"
    # success_message = "Notice have been created successfully."

    def form_valid(self, form):
        faculty = get_object_or_404(FacultyDetail, user__id=self.request.user.id)
        notice_for = self.request.POST.getlist('notice_for')
        course_branch_year = " ".join(notice_for)
        form.instance.faculty = faculty
        form.instance.course_branch_year = course_branch_year
        form.save()
        messages.success(self.request, 'Notice created successfully.')
        return super(CreateView, self).form_valid(form)
    
    def dispatch(self, request, *args, **kwargs):
        try:
            FacultyDetail.objects.get(user__id=self.request.user.id)
        except:
            raise PermissionDenied
        return super(CreateNotice, self).dispatch(request, *args, **kwargs)


class NoticeUpdateView(LoginRequiredMixin, UpdateView):
    model = Notice
    form_class = NoticeCreateForm
    template_name = 'notices/notice_create.html'
    success_url = reverse_lazy('my-uploaded-notices')

    def get_queryset(self):
        base_queryset = super(NoticeUpdateView, self).get_queryset()
        notice = Notice.objects.get(id=self.kwargs['pk'])
        if self.request.user == notice.faculty.user:
            return base_queryset
        else:
            raise PermissionDenied()

    def form_valid(self, form):
        notice_for = self.request.POST.getlist('notice_for')
        course_branch_year = " ".join(notice_for)
        form.instance.course_branch_year = course_branch_year
        form.save()
        messages.success(self.request, 'Notice updated successfully.')
        return super(NoticeUpdateView, self).form_valid(form)


class NoticeDeleteView(LoginRequiredMixin, DeleteView):
    model = Notice
    success_url = reverse_lazy('notice-list')

    def delete(self, *args, **kwargs):
        messages.success(self.request, 'Notice deleted successfully.')
        return super(NoticeDeleteView, self).delete(self.get_object())


class BookmarkCreateView(LoginRequiredMixin, generic.View):
    '''
            Adding a Bookmark to a notice
    '''
    def post(self, request, pk=None):
        notice = Notice.objects.get(pk=pk)
        obj, created = BookmarkedNotice.objects.get_or_create(
            user=self.request.user,
            notice=notice)
        if created:
            return HttpResponse("Successfully Bookmarked")
        else:
            return HttpResponse("You have already bookmarked this notice")


class BookmarkListView(LoginRequiredMixin, generic.ListView):
    model = BookmarkedNotice
    """
        View for listing the bookmarked notices
    """

    def get(self, request):
        template_name = "bookmark.html"
        bookmark_list = BookmarkedNotice.objects.filter(user=request.user).order_by('-pinned')
        paginator = Paginator(bookmark_list, constants.NOTICES_TO_DISPLAY_ON_SINGLE_PAGE)
        page = request.GET.get('page')
        try:
            bookmarks = paginator.page(page)
        except PageNotAnInteger:
            bookmarks = paginator.page(1)
        except EmptyPage:
            bookmarks = paginator.page(paginator.num_pages)
        return render(request, template_name, {"notices": bookmarks})


class BookmarkDeleteView(LoginRequiredMixin, DeleteView):
    '''
            Deleting a notice from Bookmark Notices List
    '''

    def post(self, request, pk=None):
        try:
            notice = get_object_or_404(Notice, pk=pk)
            BookmarkedNotice.objects.filter(user=self.request.user, notice=notice)[0].delete()
            messages.success(self.request, 'Bookmark removed.')
            return HttpResponse("Deleted the notice Successfully")
        except:
            messages.success(self.request, 'Some error occured.')
            return HttpResponse("Some error occured. Please try after sometime.")


class PinCreateView(LoginRequiredMixin, generic.View):

    def post(self, request, pk=None):
        try:
            '''
            only one pin is used for top so replacing the previous top pinned item to new one
            '''
            try:
                previous = BookmarkedNotice.objects.get(user=request.user, pinned=True)
                previous.pinned = False
                previous.save()
            except:
                pass

            bookmark = BookmarkedNotice.objects.get(pk=pk)
            bookmark.pinned = True
            bookmark.save()
            return HttpResponse("Pinned To Top")

        except:
            return HttpResponse("Some error occured.Please try after sometime")


class ReleventNoticeListView(LoginRequiredMixin, generic.View):

    def get(self, request):
        template_name = "notices/list.html"
        page_type = 'Relevant'
        try:
            faculty = get_object_or_404(FacultyDetail, user__id=self.request.user.id)
            notices = Notice.objects.filter(
                Q(course_branch_year__contains=faculty.department) | Q(course_branch_year__contains='-AllBranches-') | Q(course_branch_year__contains='-AllBranches-')
            )
        except:
            notices = Notice.objects.all()
            student = get_object_or_404(StudentDetail, user__id=self.request.user.id)
            notices.filter(Q(course_branch_year__contains=student.course+"-") | Q(course_branch_year__contains='AllCourses-'))
            notices.filter(Q(course_branch_year__contains="-"+student.branch+"-") | Q(course_branch_year__contains='-AllBranches-'))
            notices.filter(Q(course_branch_year__contains="-"+str(student.year)+"-") | Q(course_branch_year__contains='-AllYears-'))

        paginator = Paginator(notices, 10)

        page = request.GET.get('page')
        try:
            notices = paginator.page(page)
        except PageNotAnInteger:
            # If page is not an integer, deliver first page.
            notices = paginator.page(1)
        except EmptyPage:
            # If page is out of range (e.g. 9999), deliver last page of results.
            notices = paginator.page(paginator.num_pages)

        return render(request, template_name, {'notices': notices, 'page_type':page_type})

    def post(self, request, *args, **kwargs):
        notice = Notice.objects.filter(id=request.POST['notice_id'])[0]
        context = {
            'faculty': notice.faculty.user.username,
            'title': notice.title,
            'description': notice.description,
            # 'file' : notice.file_attached,
            'subject': notice.subject,
            'date': str(notice.modified).split(' ')[0]
        }
        return JsonResponse(context)


class SearchNotices(LoginRequiredMixin, generic.View):

    def post(self, request, *args, **kwargs):

        template = 'notices/list.html'

        title = request.POST.get('title', "")
        description = request.POST.get('description', "")
        faculty = request.POST.get('faculty', "")
        course = request.POST.get('course', "")
        branch = request.POST.get('branch', "")
        year = request.POST.get('year', "")
        section = request.POST.get('section', "")
        # Get date range from desktop version
        date_desktop = request.POST.get('date_desktop', "")
        date_m_end = ""
        date_m_start = ""

        if date_desktop == "":
            # Get date range from mobile version
            date_m_end = request.POST.get('date_m_end', "")
            date_m_start = request.POST.get('date_m_start', "")

        Notices = Notice.objects.all()

        if title != "":
            Notices = Notices.filter(title__contains=title)

        if description != "":
            Notices = Notices.filter(description__contains=description)

        if faculty != "":
            Notices = Notices.filter(
                Q(faculty__user__username__contains=faculty) |
                Q(faculty__user__first_name__contains=faculty) |
                Q(faculty__user__last_name__contains=faculty))

        if course != "":
            Notices = Notices.filter(course_branch_year__contains=course+"-")

        if branch != "":
            Notices = Notices.filter(course_branch_year__contains="-"+branch+"-")

        if year != "":
            Notices = Notices.filter(course_branch_sem__contains="-"+year+"-")

        if section != "":
            Notices = Notices.filter(course_branch_sem__contains="-"+section)

        if date_desktop != "":
            start_date_list = date_desktop.split('-')[0]
            start_date = datetime.strptime(start_date_list, "%d/%m/%Y")
            end_date_list = date_desktop.split('-')[1]
            end_date = datetime.strptime(end_date_list, "%d/%m/%Y")

            Notices = Notices.filter(modified__range=(start_date, end_date))

        elif date_m_start != "" or date_m_end != "":
            # To be done
            start_date = datetime.strptime(date_m_start, "%m/%d/%Y")
            end_date = datetime.strptime(date_m_end, "%m/%d/%Y")
            Notices = Notices.filter(modified__range=(start_date, end_date))

        Notices = Notices.order_by('-modified')

        paginator = Paginator(Notices, constants.NOTICES_TO_DISPLAY_ON_SINGLE_PAGE)
        page = request.GET.get('page')
        try:
            notices = paginator.page(page)
        except PageNotAnInteger:
            # If page is not an integer, deliver first page.
            notices = paginator.page(1)
        except EmptyPage:
            # If page is out of range (e.g. 9999), deliver last page of results.
            notices = paginator.page(paginator.num_pages)

        return render(request, template, {'notices': notices})


class MyUploadedNotices(LoginRequiredMixin, generic.View):

    def get(self, request):
        faculty = get_object_or_404(FacultyDetail, user__id=self.request.user.id)
        template = 'notices/my_uploaded_notices.html'
        notice_list = Notice.objects.filter(faculty__user=faculty.user).order_by('-modified')
        bookmark_id_list = BookmarkedNotice.objects.filter(user=faculty.user).values_list('notice__pk', flat=True)

        # To check if the notices are bookmarked by user or not
        for notice in notice_list:
            for bookmark_id in bookmark_id_list:
                if bookmark_id == notice.pk:
                    notice.is_bookmarked_by_user = True
                    break
                else:
                    notice.is_bookmarked_by_user = False

        paginator = Paginator(notice_list, constants.NOTICES_TO_DISPLAY_ON_SINGLE_PAGE)
        page = request.GET.get('page')
        try:
            notices = paginator.page(page)
        except PageNotAnInteger:
            # If page is not an integer, deliver first page.
            notices = paginator.page(1)
        except EmptyPage:
            # If page is out of range (e.g. 9999), deliver last page of results.
            notices = paginator.page(paginator.num_pages)
        return render(request, template, {"notices": notices})
