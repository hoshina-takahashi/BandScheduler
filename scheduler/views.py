import json
from datetime import date, timedelta
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from .models import (
    Room, Member, Schedule, RecurringSchedule,
    PersonalSchedule, PersonalRecurringSchedule
)

WEEKDAY_LABELS = ['月', '火', '水', '木', '金', '土', '日']
WEEKDAY_FULL = ['月曜日', '火曜日', '水曜日', '木曜日', '金曜日', '土曜日', '日曜日']


def _week_days(week_offset=0):
    today = date.today()
    monday = today - timedelta(days=today.weekday()) + timedelta(weeks=week_offset)
    return [monday + timedelta(days=i) for i in range(7)]


def _expand_recurring(recurring_qs, days):
    """定期予定を指定週の日付に展開する"""
    result = []
    for r in recurring_qs:
        for day in days:
            if day.weekday() == r.weekday:
                result.append({
                    'id': r.id,
                    'date': day.strftime('%Y-%m-%d'),
                    'start_time': r.start_time.strftime('%H:%M'),
                    'end_time': r.end_time.strftime('%H:%M'),
                    'label': r.label or '定期予定',
                    'is_recurring': True,
                })
    return result


# ==================== マイカレンダー ====================

@login_required
def my_calendar(request):
    week_offset = int(request.GET.get('week', 0))
    days = _week_days(week_offset)
    today = date.today()

    schedules = PersonalSchedule.objects.filter(
        user=request.user,
        date__range=[days[0], days[6]]
    )
    recurring = PersonalRecurringSchedule.objects.filter(user=request.user)

    schedules_json = [
        {
            'id': s.id,
            'date': s.date.strftime('%Y-%m-%d'),
            'start_time': s.start_time.strftime('%H:%M'),
            'end_time': s.end_time.strftime('%H:%M'),
            'label': s.label,
            'is_recurring': False,
        }
        for s in schedules
    ]
    schedules_json += _expand_recurring(recurring, days)

    return render(request, 'scheduler/my_calendar.html', {
        'days': days,
        'today': today,
        'week_offset': week_offset,
        'schedules_json': json.dumps(schedules_json, ensure_ascii=False),
        'current_tab': 'my_calendar',
    })


# ==================== 定期予定 ====================

@login_required
def recurring(request):
    recurring_list = PersonalRecurringSchedule.objects.filter(user=request.user)
    recurring_json = [
        {
            'id': r.id,
            'weekday': r.weekday,
            'weekday_label': WEEKDAY_FULL[r.weekday],
            'start_time': r.start_time.strftime('%H:%M'),
            'end_time': r.end_time.strftime('%H:%M'),
            'label': r.label,
        }
        for r in recurring_list
    ]
    return render(request, 'scheduler/recurring.html', {
        'recurring_json': json.dumps(recurring_json, ensure_ascii=False),
        'current_tab': 'recurring',
    })


# ==================== グループ作成 ====================

@login_required
def group_create(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        start_date = request.POST.get('start_date') or None
        end_date = request.POST.get('end_date') or None
        candidate_dates = request.POST.getlist('candidate_dates')

        if name:
            room = Room.objects.create(
                name=name,
                created_by=request.user,
                start_date=start_date,
                end_date=end_date,
                candidate_dates=sorted(candidate_dates),
            )
            # ホストをメンバーに追加
            Member.objects.create(
                room=room,
                user=request.user,
                name=request.user.first_name or request.user.email.split('@')[0],
            )
            return redirect('scheduler:group_calendar', room_id=room.id)
    return render(request, 'scheduler/group_create.html', {'current_tab': 'group_create'})


# ==================== カレンダー一覧 ====================

@login_required
def group_list(request):
    memberships = Member.objects.filter(user=request.user).select_related('room').order_by('-room__created_at')
    return render(request, 'scheduler/group_list.html', {
        'memberships': memberships,
        'current_tab': 'group_list',
    })


# ==================== ユーザー設定 ====================

@login_required
def user_settings(request):
    if request.method == 'POST':
        display_name = request.POST.get('display_name', '').strip()
        if display_name:
            request.user.first_name = display_name
            request.user.save()
        return redirect('scheduler:user_settings')
    return render(request, 'scheduler/user_settings.html', {'current_tab': 'user_settings'})


# ==================== グループカレンダー ====================

@login_required
def group_calendar(request, room_id):
    room = get_object_or_404(Room, id=room_id)

    # 未参加の場合は参加ページへ
    try:
        current_member = Member.objects.get(room=room, user=request.user)
    except Member.DoesNotExist:
        return redirect('scheduler:join', room_id=room.id)

    week_offset = int(request.GET.get('week', 0))
    days = _week_days(week_offset)
    today = date.today()

    # 全メンバーの予定を集約（PersonalSchedule + PersonalRecurringSchedule）
    all_schedules = []
    members = room.members.filter(user__isnull=False).select_related('user')

    for member in members:
        is_mine = (member.user == request.user)
        # 個人予定
        for s in PersonalSchedule.objects.filter(user=member.user, date__range=[days[0], days[6]]):
            all_schedules.append({
                'member_name': member.name,
                'is_mine': is_mine,
                'date': s.date.strftime('%Y-%m-%d'),
                'start_time': s.start_time.strftime('%H:%M'),
                'end_time': s.end_time.strftime('%H:%M'),
                'label': s.label,
                'is_recurring': False,
            })
        # 定期予定を展開
        for item in _expand_recurring(
            PersonalRecurringSchedule.objects.filter(user=member.user), days
        ):
            item['member_name'] = member.name
            item['is_mine'] = is_mine
            all_schedules.append(item)

    # 候補日
    candidate_dates = room.candidate_dates or []

    return render(request, 'scheduler/group_calendar.html', {
        'room': room,
        'current_member': current_member,
        'members': members,
        'days': days,
        'today': today,
        'week_offset': week_offset,
        'schedules_json': json.dumps(all_schedules, ensure_ascii=False),
        'candidate_dates': json.dumps(candidate_dates),
        'current_tab': 'group_list',
    })


# ==================== ルーム参加 ====================

@login_required
def join(request, room_id):
    room = get_object_or_404(Room, id=room_id)

    # 既に参加済みならカレンダーへ
    if Member.objects.filter(room=room, user=request.user).exists():
        return redirect('scheduler:group_calendar', room_id=room.id)

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        if not name:
            name = request.user.first_name or request.user.email.split('@')[0]
        Member.objects.create(room=room, user=request.user, name=name)
        return redirect('scheduler:group_calendar', room_id=room.id)

    default_name = request.user.first_name or request.user.email.split('@')[0]
    return render(request, 'scheduler/join.html', {
        'room': room,
        'default_name': default_name,
    })


# ==================== API ====================

@login_required
@require_POST
def personal_schedule_api(request):
    data = json.loads(request.body)
    action = data.get('action')

    if action == 'add':
        s = PersonalSchedule.objects.create(
            user=request.user,
            date=data['date'],
            start_time=data['start_time'],
            end_time=data['end_time'],
            label=data.get('label', ''),
        )
        return JsonResponse({'status': 'ok', 'id': s.id})

    if action == 'delete':
        PersonalSchedule.objects.filter(id=data['id'], user=request.user).delete()
        return JsonResponse({'status': 'ok'})

    return JsonResponse({'error': '不明なアクション'}, status=400)


@login_required
@require_POST
def personal_recurring_api(request):
    data = json.loads(request.body)
    action = data.get('action')

    if action == 'add':
        r = PersonalRecurringSchedule.objects.create(
            user=request.user,
            weekday=int(data['weekday']),
            start_time=data['start_time'],
            end_time=data['end_time'],
            label=data.get('label', ''),
        )
        return JsonResponse({
            'status': 'ok',
            'id': r.id,
            'weekday_label': WEEKDAY_FULL[r.weekday],
        })

    if action == 'delete':
        PersonalRecurringSchedule.objects.filter(id=data['id'], user=request.user).delete()
        return JsonResponse({'status': 'ok'})

    return JsonResponse({'error': '不明なアクション'}, status=400)


@login_required
@require_POST
def schedule_save(request, room_id):
    """旧API（後方互換用）"""
    return JsonResponse({'status': 'ok'})


@login_required
@require_POST
def group_delete(request, room_id):
    room = get_object_or_404(Room, id=room_id, created_by=request.user)
    room.delete()
    return redirect('scheduler:group_list')
