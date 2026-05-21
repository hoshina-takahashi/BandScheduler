from django.shortcuts import render, get_object_or_404
from .models import Group, Schedule

def index(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        if name:
            group = Group.objects.create(name=name)
            return redirect('scheduler:calendar', slug=group.slug)

    groups = Group.objects.all().order_by('-created_at')
    return render(request, 'scheduler/index.html', {'groups': groups})
def calendar(request, slug):
    group = get_object_or_404(Group, slug=slug)
    schedules = Schedule.objects.filter(group=group)

    # 日付ごとに予定をまとめる
    from collections import defaultdict
    from datetime import time

    schedule_by_date = defaultdict(list)
    for s in schedules:
        schedule_by_date[s.date].append(s)

    # 各日付の空き時間を計算（9〜21時を1時間単位で）
    slots = list(range(9, 21))  # [9, 10, 11, ..., 20]
    free_slots_by_date = {}

    for date, day_schedules in schedule_by_date.items():
        free = []
        for hour in slots:
            slot_start = time(hour, 0)
            slot_end = time(hour + 1, 0)
            # このスロットに誰か被っているか確認
            is_busy = any(
                s.start_time <= slot_start and s.end_time >= slot_end
                for s in day_schedules
            )
            if not is_busy:
                free.append(hour)
        free_slots_by_date[date] = free

    return render(request, 'scheduler/calendar.html', {
        'group': group,
        'schedules': schedules,
        'free_slots_by_date': free_slots_by_date,
    })
from django.shortcuts import render, get_object_or_404, redirect

def input_schedule(request, slug):
    group = get_object_or_404(Group, slug=slug)

    if request.method == 'POST':
        user_name = request.POST.get('user_name')
        date = request.POST.get('date')
        start_time = request.POST.get('start_time')
        end_time = request.POST.get('end_time')
        label = request.POST.get('label', '')

        Schedule.objects.create(
            group=group,
            user_name=user_name,
            date=date,
            start_time=start_time,
            end_time=end_time,
            label=label,
        )
        return redirect('scheduler:calendar', slug=slug)

    return render(request, 'scheduler/input.html', {'group': group})