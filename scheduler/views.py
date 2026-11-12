# scheduler/views.py
import json
from datetime import date, timedelta, datetime
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import Room, Member, Schedule, RecurringSchedule
from .forms import RoomCreateForm, MemberJoinForm


def top(request):
    return render(request, 'scheduler/top.html')


def room_create(request):
    if request.method == 'POST':
        form = RoomCreateForm(request.POST)
        if form.is_valid():
            room = form.save()
            return redirect('scheduler:join', room_id=room.id)
    else:
        form = RoomCreateForm()
    return render(request, 'scheduler/room_create.html', {'form': form})


def join(request, room_id):
    room = get_object_or_404(Room, id=room_id)
    if request.method == 'POST':
        form = MemberJoinForm(request.POST)
        if form.is_valid():
            member = Member.objects.create(
                room=room,
                name=form.cleaned_data['name']
            )
            request.session['member_id'] = member.id
            return redirect('scheduler:calendar', room_id=room.id)
    else:
        form = MemberJoinForm()
    return render(request, 'scheduler/join.html', {'room': room, 'form': form})


def _get_current_member(request, room):
    """セッションからメンバーを取得する共通処理"""
    member_id = request.session.get('member_id')
    if not member_id:
        return None
    try:
        return Member.objects.get(id=member_id, room=room)
    except Member.DoesNotExist:
        return None


def _expand_recurring(member, days):
    """
    定期予定をその週の日付に展開してScheduleと同じ形式のdictリストで返す。
    DBには保存しない（表示専用）。
    id は負の値にして通常のScheduleと区別する。
    """
    result = []
    recurring = RecurringSchedule.objects.filter(member=member)
    for r in recurring:
        for day in days:
            if day.weekday() == r.weekday:
                result.append({
                    'id': -r.id,  # 負の値で定期予定と識別
                    'member_id': member.id,
                    'member_name': member.name,
                    'date': day.strftime('%Y-%m-%d'),
                    'start_time': r.start_time.strftime('%H:%M'),
                    'end_time': r.end_time.strftime('%H:%M'),
                    'label': r.label or '定期予定',
                    'is_mine': True,
                    'is_recurring': True,
                    'recurring_id': r.id,
                })
    return result


def calendar(request, room_id):
    room = get_object_or_404(Room, id=room_id)
    current_member = _get_current_member(request, room)
    if not current_member:
        return redirect('scheduler:join', room_id=room.id)

    today = date.today()
    week_offset = int(request.GET.get('week', 0))
    monday = today - timedelta(days=today.weekday()) + timedelta(weeks=week_offset)
    days = [monday + timedelta(days=i) for i in range(7)]

    # 通常の予定を取得
    schedules = Schedule.objects.filter(
        member__room=room,
        date__range=[days[0], days[6]]
    ).select_related('member')

    schedules_json = [
        {
            'id': s.id,
            'member_id': s.member.id,
            'member_name': s.member.name,
            'date': s.date.strftime('%Y-%m-%d'),
            'start_time': s.start_time.strftime('%H:%M'),
            'end_time': s.end_time.strftime('%H:%M'),
            'label': s.label,
            'is_mine': s.member.id == current_member.id,
            'is_recurring': False,
        }
        for s in schedules
    ]

    # 全メンバーの定期予定をこの週に展開して追加
    for member in room.members.all():
        schedules_json += _expand_recurring(member, days)

    # 自分の定期予定一覧（設定画面表示用）
    my_recurring = RecurringSchedule.objects.filter(member=current_member)
    recurring_json = [
        {
            'id': r.id,
            'weekday': r.weekday,
            'weekday_label': r.get_weekday_display(),
            'start_time': r.start_time.strftime('%H:%M'),
            'end_time': r.end_time.strftime('%H:%M'),
            'label': r.label,
        }
        for r in my_recurring
    ]

    return render(request, 'scheduler/calendar.html', {
        'room': room,
        'current_member': current_member,
        'members': room.members.all(),
        'days': days,
        'week_offset': week_offset,
        'schedules_json': json.dumps(schedules_json, ensure_ascii=False),
        'recurring_json': json.dumps(recurring_json, ensure_ascii=False),
        'today': today,
    })


@require_POST
def schedule_save(request, room_id):
    room = get_object_or_404(Room, id=room_id)
    current_member = _get_current_member(request, room)
    if not current_member:
        return JsonResponse({'error': '未参加です'}, status=403)

    data = json.loads(request.body)
    action = data.get('action')

    if action == 'add':
        schedule = Schedule.objects.create(
            member=current_member,
            date=data['date'],
            start_time=data['start_time'],
            end_time=data['end_time'],
            label=data.get('label', ''),
        )
        return JsonResponse({'status': 'ok', 'id': schedule.id})

    if action == 'delete':
        Schedule.objects.filter(
            id=data['id'],
            member=current_member
        ).delete()
        return JsonResponse({'status': 'ok'})

    if action == 'add_recurring':
        r = RecurringSchedule.objects.create(
            member=current_member,
            weekday=data['weekday'],
            start_time=data['start_time'],
            end_time=data['end_time'],
            label=data.get('label', ''),
        )
        return JsonResponse({
            'status': 'ok',
            'id': r.id,
            'weekday_label': r.get_weekday_display(),
        })

    if action == 'delete_recurring':
        RecurringSchedule.objects.filter(
            id=data['id'],
            member=current_member
        ).delete()
        return JsonResponse({'status': 'ok'})

    return JsonResponse({'error': '不明なアクション'}, status=400)