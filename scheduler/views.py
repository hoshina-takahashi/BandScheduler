import json
import datetime as dt
from datetime import date, timedelta
from zoneinfo import ZoneInfo
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.urls import reverse
from django.utils import timezone
from .models import (
    Room, Member, Schedule, RecurringSchedule,
    PersonalSchedule, PersonalRecurringSchedule,
    GoogleCalendarToken,
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
    gcal_token = GoogleCalendarToken.objects.filter(user=request.user).first()
    gcal_sync_error = request.session.pop('gcal_sync_error', None)
    return render(request, 'scheduler/user_settings.html', {
        'current_tab': 'user_settings',
        'gcal_token': gcal_token,
        'gcal_sync_error': gcal_sync_error,
    })


# ==================== グループカレンダー ====================

CALENDAR_HOURS = list(range(7, 23))  # 7:00〜22:00


@login_required
def group_calendar(request, room_id):
    room = get_object_or_404(Room, id=room_id)

    # 未参加の場合は参加ページへ
    try:
        current_member = Member.objects.get(room=room, user=request.user)
    except Member.DoesNotExist:
        return redirect('scheduler:join', room_id=room.id)

    week_offset = int(request.GET.get('week', 0))
    raw_days = _week_days(week_offset)
    today = date.today()

    members = list(room.members.filter(user__isnull=False).select_related('user'))
    member_count = len(members)

    # 週全体の予定を一括取得（N+1クエリ回避）
    user_ids = [m.user_id for m in members]
    all_personal = list(PersonalSchedule.objects.filter(
        user_id__in=user_ids, date__range=[raw_days[0], raw_days[6]]
    ))
    all_recurring = list(PersonalRecurringSchedule.objects.filter(user_id__in=user_ids))

    user_to_member = {m.user_id: m for m in members}

    # 日ごとの表示データを構築
    days = []
    for d in raw_days:
        weekday_int = d.weekday()
        day_personal = [s for s in all_personal if s.date == d]
        day_recurring = [r for r in all_recurring if r.weekday == weekday_int]

        schedules_for_day = []
        member_busy = {m.user_id: set() for m in members}

        for s in day_personal:
            m = user_to_member.get(s.user_id)
            if not m:
                continue
            is_mine = (s.user_id == request.user.id)
            s_start_min = s.start_time.hour * 60 + s.start_time.minute
            s_end_min = s.end_time.hour * 60 + s.end_time.minute
            for h in CALENDAR_HOURS:
                if h * 60 >= s_start_min and h * 60 < s_end_min:
                    member_busy[s.user_id].add(h)
            schedules_for_day.append({
                'start_hour': s.start_time.hour,
                'height': max(20, s_end_min - s_start_min),
                'type': 'self-sched' if is_mine else 'other-sched',
                'label': s.label or ('自分' if is_mine else m.name),
            })

        for r in day_recurring:
            m = user_to_member.get(r.user_id)
            if not m:
                continue
            is_mine = (r.user_id == request.user.id)
            r_start_min = r.start_time.hour * 60 + r.start_time.minute
            r_end_min = r.end_time.hour * 60 + r.end_time.minute
            for h in CALENDAR_HOURS:
                if h * 60 >= r_start_min and h * 60 < r_end_min:
                    member_busy[r.user_id].add(h)
            schedules_for_day.append({
                'start_hour': r.start_time.hour,
                'height': max(20, r_end_min - r_start_min),
                'type': 'self-sched' if is_mine else 'recurring-sched',
                'label': r.label or ('自分' if is_mine else m.name),
            })

        busy_counts = {h: sum(1 for uid, bh in member_busy.items() if h in bh) for h in CALENDAR_HOURS}
        all_free_hours = [h for h in CALENDAR_HOURS if member_count > 0 and busy_counts[h] == 0]

        days.append({
            'date': d.strftime('%Y-%m-%d'),
            'day': d.day,
            'weekday': WEEKDAY_LABELS[weekday_int],
            'is_today': d == today,
            'schedules': schedules_for_day,
            'all_free_hours': all_free_hours,
        })

    # 週ラベルとナビゲーション
    week_label = f"{raw_days[0].month}月{raw_days[0].day}日〜{raw_days[-1].month}月{raw_days[-1].day}日"

    # 候補日（Pythonリストのまま渡す → テンプレートで {% if candidate_dates %} が正確に動く）
    candidate_dates = room.candidate_dates or []

    # 候補日ごとの空き状況を計算して candidate_data を構築
    candidate_data = []
    if candidate_dates:
        from datetime import date as _date
        cand_date_objs = []
        for ds in candidate_dates:
            try:
                cand_date_objs.append(_date.fromisoformat(ds))
            except (ValueError, TypeError):
                pass
        if cand_date_objs:
            min_d, max_d = min(cand_date_objs), max(cand_date_objs)
            cand_personal = list(PersonalSchedule.objects.filter(
                user_id__in=user_ids, date__range=[min_d, max_d]
            ))
            for d in cand_date_objs:
                weekday_int = d.weekday()
                day_personal = [s for s in cand_personal if s.date == d]
                day_recurring = [r for r in all_recurring if r.weekday == weekday_int]
                member_busy = {m.user_id: set() for m in members}
                for s in day_personal:
                    s_start = s.start_time.hour * 60 + s.start_time.minute
                    s_end = s.end_time.hour * 60 + s.end_time.minute
                    for h in CALENDAR_HOURS:
                        if s_start <= h * 60 < s_end:
                            member_busy[s.user_id].add(h)
                for r in day_recurring:
                    r_start = r.start_time.hour * 60 + r.start_time.minute
                    r_end = r.end_time.hour * 60 + r.end_time.minute
                    for h in CALENDAR_HOURS:
                        if r_start <= h * 60 < r_end:
                            member_busy[r.user_id].add(h)
                slots = []
                all_free_count = 0
                for h in CALENDAR_HOURS:
                    busy_count = sum(1 for bh in member_busy.values() if h in bh)
                    if busy_count == 0:
                        status = 'free'
                        all_free_count += 1
                    elif member_count > 0 and busy_count == member_count:
                        status = 'busy'
                    else:
                        status = 'partial'
                    slots.append({'hour': h, 'time': f'{h}:00', 'time_end': f'{h+1}:00', 'status': status})
                member_sched_list = [
                    {
                        'name': m.name,
                        'is_mine': m.user_id == request.user.id,
                        'busy_hours': sorted(member_busy.get(m.user_id, set())),
                    }
                    for m in members
                ]
                candidate_data.append({
                    'date_str': f'{d.month}月{d.day}日',
                    'weekday': WEEKDAY_LABELS[weekday_int],
                    'slots': slots,
                    'all_free_count': all_free_count,
                    'all_day_free': all_free_count == len(CALENDAR_HOURS),
                    'member_schedules': member_sched_list,
                })

    # JS用フラットJSON
    all_schedules_js = []
    for m in members:
        is_mine = (m.user == request.user)
        for s in [s for s in all_personal if s.user_id == m.user_id]:
            all_schedules_js.append({
                'member_name': m.name, 'is_mine': is_mine,
                'date': s.date.strftime('%Y-%m-%d'),
                'start_time': s.start_time.strftime('%H:%M'),
                'end_time': s.end_time.strftime('%H:%M'),
                'label': s.label, 'is_recurring': False,
            })
        for item in _expand_recurring([r for r in all_recurring if r.user_id == m.user_id], raw_days):
            item['member_name'] = m.name
            item['is_mine'] = is_mine
            all_schedules_js.append(item)

    return render(request, 'scheduler/group_calendar.html', {
        'room': room,
        'current_member': current_member,
        'members': members,
        'days': days,
        'hours': CALENDAR_HOURS,
        'today': today,
        'week_offset': week_offset,
        'prev_week': week_offset - 1,
        'next_week': week_offset + 1,
        'week_label': week_label,
        'schedules_json': json.dumps(all_schedules_js, ensure_ascii=False),
        'candidate_dates': candidate_dates,
        'candidate_data': candidate_data,
        'candidate_detail_json': json.dumps([
            {'date_str': item['date_str'], 'weekday': item['weekday'], 'members': item.get('member_schedules', [])}
            for item in candidate_data
        ], ensure_ascii=False),
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


@login_required
@require_POST
def group_leave(request, room_id):
    room = get_object_or_404(Room, id=room_id)
    Member.objects.filter(room=room, user=request.user).delete()
    return redirect('scheduler:group_list')


# ==================== Google カレンダー連携 ====================

GCAL_SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']


def _build_gcal_flow(request):
    """allauth の SocialApp から Google OAuth Flow を生成する"""
    from allauth.socialaccount.models import SocialApp
    from google_auth_oauthlib.flow import Flow
    app = SocialApp.objects.get(provider='google')
    callback_url = request.build_absolute_uri(reverse('scheduler:gcal_callback'))
    flow = Flow.from_client_config(
        {
            'web': {
                'client_id': app.client_id,
                'client_secret': app.secret,
                'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
                'token_uri': 'https://oauth2.googleapis.com/token',
                'redirect_uris': [callback_url],
            }
        },
        scopes=GCAL_SCOPES,
        redirect_uri=callback_url,
    )
    return flow


@login_required
def gcal_auth(request):
    """Google カレンダー OAuth 開始"""
    flow = _build_gcal_flow(request)
    auth_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent',
    )
    request.session['gcal_oauth_state'] = state
    return redirect(auth_url)


@login_required
def gcal_callback(request):
    """Google OAuth コールバック — トークンを保存して設定ページへ"""
    if 'error' in request.GET:
        return redirect('scheduler:user_settings')

    try:
        flow = _build_gcal_flow(request)
        # state検証をスキップ（再ログイン時のセッションリセット対策）
        flow.fetch_token(code=request.GET.get('code'))
        creds = flow.credentials
        GoogleCalendarToken.objects.update_or_create(
            user=request.user,
            defaults={
                'access_token': creds.token,
                'refresh_token': creds.refresh_token or '',
                'token_expiry': creds.expiry,
            }
        )
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f'gcal_callback error: {e}')

    return redirect('scheduler:user_settings')


@login_required
@require_POST
def gcal_sync(request):
    """Google カレンダーの予定を PersonalSchedule に同期する"""
    from allauth.socialaccount.models import SocialApp
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request as GoogleRequest
    from googleapiclient.discovery import build

    try:
        token_obj = GoogleCalendarToken.objects.get(user=request.user)
    except GoogleCalendarToken.DoesNotExist:
        return redirect('scheduler:gcal_auth')

    try:
        app = SocialApp.objects.get(provider='google')
        creds = Credentials(
            token=token_obj.access_token,
            refresh_token=token_obj.refresh_token or None,
            token_uri='https://oauth2.googleapis.com/token',
            client_id=app.client_id,
            client_secret=app.secret,
            scopes=GCAL_SCOPES,
        )

        # トークンが失効していたらリフレッシュ
        if not creds.valid and creds.refresh_token:
            creds.refresh(GoogleRequest())
            token_obj.access_token = creds.token
            token_obj.token_expiry = creds.expiry
            token_obj.save()

        service = build('calendar', 'v3', credentials=creds)

        jst = ZoneInfo('Asia/Tokyo')
        now = dt.datetime.now(dt.timezone.utc)
        end = now + dt.timedelta(days=30)

        events_result = service.events().list(
            calendarId='primary',
            timeMin=now.isoformat(),
            timeMax=end.isoformat(),
            singleEvents=True,
            orderBy='startTime',
        ).execute()
        events = events_result.get('items', [])

        # 既存のGoogle同期予定を今日以降で削除
        today = dt.date.today()
        PersonalSchedule.objects.filter(
            user=request.user,
            date__gte=today,
            source='google',
        ).delete()

        # イベントをインポート（終日予定はスキップ）
        for event in events:
            start = event.get('start', {})
            end_ev = event.get('end', {})
            if 'dateTime' not in start:
                continue
            summary = event.get('summary', '予定')[:100]
            start_dt = dt.datetime.fromisoformat(
                start['dateTime'].replace('Z', '+00:00')
            ).astimezone(jst)
            end_dt = dt.datetime.fromisoformat(
                end_ev['dateTime'].replace('Z', '+00:00')
            ).astimezone(jst)
            PersonalSchedule.objects.create(
                user=request.user,
                date=start_dt.date(),
                start_time=start_dt.time().replace(second=0, microsecond=0),
                end_time=end_dt.time().replace(second=0, microsecond=0),
                label=summary,
                source='google',
            )

        token_obj.synced_at = timezone.now()
        token_obj.save()

    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f'gcal_sync error: {e}')
        # セッションにエラーメッセージを保存
        request.session['gcal_sync_error'] = str(e)

    return redirect('scheduler:user_settings')


@login_required
@require_POST
def gcal_disconnect(request):
    """Google カレンダー連携を解除し、同期済み予定も削除する"""
    PersonalSchedule.objects.filter(user=request.user, source='google').delete()
    GoogleCalendarToken.objects.filter(user=request.user).delete()
    return redirect('scheduler:user_settings')
