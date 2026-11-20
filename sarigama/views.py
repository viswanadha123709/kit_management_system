from django.shortcuts import render
from django.http import HttpResponse
from datetime import timedelta, datetime
from django.utils import timezone
from . import models
import threading
import json
from django.db import transaction


def parse_kit_items(raw_items):
    """Safely parse kit items into a list of integer instrument IDs."""
    if raw_items is None:
        return []
    if isinstance(raw_items, str):
        raw_items = raw_items.strip()
        if raw_items.startswith('[') and raw_items.endswith(']'):
            try:
                raw_items = json.loads(raw_items)
            except Exception:
                raw_items = [x.strip() for x in raw_items.strip('[]').split(',') if x.strip()]
        elif ',' in raw_items:
            raw_items = [x.strip() for x in raw_items.split(',') if x.strip()]
        else:
            try:
                raw_items = [int(raw_items)]
            except ValueError:
                raw_items = []
    if isinstance(raw_items, (int, float)):
        return [int(raw_items)]
    if isinstance(raw_items, list):
        res = []
        for x in raw_items:
            try:
                res.append(int(x))
            except (ValueError, TypeError):
                pass
        return res
    return []


class user:
    @staticmethod
    def register_user(name, age, number, adhar):
        return models.user.objects.create(
            user_name=name,
            user_age=age,
            user_number=number,
            user_adhar=adhar
        )


class kit:
    @staticmethod
    def add_kit(cost, items):
        clean_items = parse_kit_items(items)
        return models.kit.objects.create(
            cost=cost,
            items=clean_items
        )

    @staticmethod
    def remove_kit(id):
        deleted, _ = models.kit.objects.filter(id=id).delete()
        return deleted > 0


class item:
    @staticmethod
    def insert_item(name, brand, specifications=""):
        return models.instrument.objects.create(
            instrument_name=name,
            brand=brand,
            specifiations=specifications or ""
        )

    @staticmethod
    def setdescreption(data, itemid):
        return models.instrument.objects.filter(id=itemid).update(
            specifiations=data
        )


class allotment(threading.Thread):

    min_gap = timedelta(minutes=15)
    min_time = timedelta(minutes=60)
    lock = threading.Lock()

    def __init__(self):
        super().__init__()

    @staticmethod
    def allot_item(kit_id, start, end, userid):

        if start >= end or end - start < allotment.min_time:
            return "Please enter a valid time period (minimum booking duration is 60 minutes)"

        kit_data = models.kit.objects.filter(id=kit_id).first()

        if kit_data is None:
            return "Kit not found"

        k_items = parse_kit_items(kit_data.items)
        if not k_items:
            return "Kit has no instruments assigned"

        for item_id in k_items:
            instrument = models.instrument.objects.filter(
                id=item_id
            ).first()

            if instrument is None:
                return f"Instrument #{item_id} not found in inventory"

            if not instrument.working:
                return f"Cannot book kit: Instrument '{instrument.instrument_name}' (ID: {instrument.id}) is faulty"

        with allotment.lock:
            with transaction.atomic():

                for i in models.schedule.objects.filter(kit_id=str(kit_id)):
                    i_start = i.start if timezone.is_aware(i.start) else timezone.make_aware(i.start)
                    i_end = i.end if timezone.is_aware(i.end) else timezone.make_aware(i.end)

                    if (
                        start < i_end + allotment.min_gap
                        and end > i_start - allotment.min_gap
                    ):
                        return "Selected slot is not available (conflicts with an existing booking or required 15-minute maintenance gap)"

                models.schedule.objects.create(
                    kit_id=str(kit_id),
                    user_id=userid,
                    start=start,
                    end=end
                )

                return "Kit booked successfully"


class inspection:

    @staticmethod
    def check_kit(kit_id):
        kit_data = models.kit.objects.filter(id=kit_id).first()

        if kit_data is None:
            return ["No such kit found"]

        k_items = parse_kit_items(kit_data.items)
        if not k_items:
            return ["Kit has no instruments assigned"]

        ans = []
        all_ok = True
        for item_id in k_items:
            instrument = models.instrument.objects.filter(
                id=item_id
            ).first()

            if instrument is None:
                ans.append(f"Instrument #{item_id} not found")
                all_ok = False
            elif not instrument.working:
                ans.append(
                    f"{instrument.instrument_name} (ID: #{instrument.id}, {instrument.brand}) is FAULTY"
                )
                all_ok = False
            else:
                ans.append(
                    f"{instrument.instrument_name} (ID: #{instrument.id}, {instrument.brand}) is WORKING"
                )

        if all_ok:
            ans.insert(0, "All instruments in this kit are working properly!")

        return ans

    @staticmethod
    def mark_default(kit_id, instrument_id):
        if kit_id:
            kit_data = models.kit.objects.filter(id=kit_id).first()
            if kit_data is None:
                return "No such kit found"
            k_items = parse_kit_items(kit_data.items)
            if instrument_id not in k_items:
                return "Instrument not present in this kit"

        updated = models.instrument.objects.filter(
            id=instrument_id
        ).update(working=False)

        if updated == 0:
            return "Instrument not found"

        return f"Instrument #{instrument_id} marked as faulty"

    @staticmethod
    def mark_working(kit_id, instrument_id):
        if kit_id:
            kit_data = models.kit.objects.filter(id=kit_id).first()
            if kit_data is None:
                return "No such kit found"
            k_items = parse_kit_items(kit_data.items)
            if instrument_id not in k_items:
                return "Instrument not present in this kit"

        updated = models.instrument.objects.filter(
            id=instrument_id
        ).update(working=True)

        if updated == 0:
            return "Instrument not found"

        return f"Instrument #{instrument_id} marked as working"


def main(request):
    ans = ""
    status_type = "info"
    active_tab = "dashboard"

    if request.method == "POST":
        action = request.POST.get("action")
        active_tab = request.POST.get("active_tab", "kits")

        try:
            if action == "register_user":
                active_tab = "users"
                name = request.POST.get("name", "").strip()
                age = int(request.POST.get("age"))
                number = int(request.POST.get("number"))
                adhar = int(request.POST.get("adhar"))
                if not name:
                    ans = "Name is required."
                    status_type = "error"
                else:
                    user.register_user(name, age, number, adhar)
                    ans = f"User '{name}' registered successfully."
                    status_type = "success"

            elif action == "add_kit":
                active_tab = "kits"
                cost = request.POST.get("cost")
                raw_items = request.POST.get("items")
                parsed_items = parse_kit_items(raw_items)
                if not parsed_items:
                    ans = "Please select or enter at least one valid instrument ID."
                    status_type = "error"
                else:
                    kit.add_kit(cost, parsed_items)
                    ans = f"Kit with {len(parsed_items)} instrument(s) added successfully."
                    status_type = "success"

            elif action == "remove_kit":
                active_tab = "kits"
                kit_id = int(request.POST.get("id"))
                if kit.remove_kit(kit_id):
                    ans = f"Kit #{kit_id} removed successfully."
                    status_type = "success"
                else:
                    ans = f"Kit #{kit_id} not found."
                    status_type = "error"

            elif action == "insert_item":
                active_tab = "items"
                name = request.POST.get("name", "").strip()
                brand = request.POST.get("brand", "").strip()
                spec = request.POST.get("specifications", request.POST.get("description", "")).strip()
                if not name or not brand:
                    ans = "Instrument name and brand are required."
                    status_type = "error"
                else:
                    new_inst = item.insert_item(name, brand, spec)
                    ans = f"Instrument '{name}' ({brand}) added successfully with ID #{new_inst.id}."
                    status_type = "success"

            elif action == "set_description":
                active_tab = "items"
                itemid = int(request.POST.get("itemid"))
                spec = request.POST.get("description", "").strip()
                count = item.setdescreption(spec, itemid)
                if count:
                    ans = f"Specifications for Instrument #{itemid} updated successfully."
                    status_type = "success"
                else:
                    ans = f"Instrument #{itemid} not found."
                    status_type = "error"

            elif action == "book_kit":
                active_tab = "booking"
                start = datetime.fromisoformat(request.POST.get("start"))
                end = datetime.fromisoformat(request.POST.get("end"))
                if timezone.is_naive(start):
                    start = timezone.make_aware(start, timezone.get_current_timezone())
                if timezone.is_naive(end):
                    end = timezone.make_aware(end, timezone.get_current_timezone())

                ans = allotment.allot_item(
                    int(request.POST.get("kit_id")),
                    start,
                    end,
                    int(request.POST.get("userid"))
                )
                if "successfully" in ans.lower():
                    status_type = "success"
                else:
                    status_type = "error"

            elif action == "check_kit":
                active_tab = "inspection"
                ans = inspection.check_kit(
                    int(request.POST.get("kit_id"))
                )
                status_type = "info"

            elif action == "mark_faulty":
                active_tab = "inspection"
                raw_kit_id = request.POST.get("kit_id")
                k_id = int(raw_kit_id) if raw_kit_id and raw_kit_id != "0" else None
                inst_id = int(request.POST.get("instrument_id"))
                ans = inspection.mark_default(k_id, inst_id)
                if "faulty" in ans.lower():
                    status_type = "success"
                else:
                    status_type = "error"

            elif action == "mark_working":
                active_tab = "inspection"
                raw_kit_id = request.POST.get("kit_id")
                k_id = int(raw_kit_id) if raw_kit_id and raw_kit_id != "0" else None
                inst_id = int(request.POST.get("instrument_id"))
                ans = inspection.mark_working(k_id, inst_id)
                if "working" in ans.lower():
                    status_type = "success"
                else:
                    status_type = "error"

            else:
                ans = "Invalid action specified."
                status_type = "error"

        except (ValueError, TypeError, json.JSONDecodeError) as e:
            ans = f"Invalid input. Please check the entered values. ({e})"
            status_type = "error"
        except Exception as e:
            ans = f"An unexpected error occurred: {e}"
            status_type = "error"

    # Enriched context queries
    users = list(models.user.objects.all().order_by("-id"))
    instruments = list(models.instrument.objects.all().order_by("id"))
    instrument_map = {inst.id: inst for inst in instruments}

    kits = list(models.kit.objects.all().order_by("id"))
    enriched_kits = []
    for k in kits:
        k_items = parse_kit_items(k.items)
        k.parsed_items = k_items
        k.instrument_list = [instrument_map[iid] for iid in k_items if iid in instrument_map]
        k.missing_ids = [iid for iid in k_items if iid not in instrument_map]
        k.faulty_list = [inst for inst in k.instrument_list if not inst.working]
        k.is_ready = len(k.missing_ids) == 0 and len(k.faulty_list) == 0 and len(k.instrument_list) > 0
        enriched_kits.append(k)

    user_map = {u.id: u for u in users}
    kit_map = {k.id: k for k in kits}
    schedules = list(models.schedule.objects.all().order_by("-start"))
    now = timezone.now()
    enriched_schedules = []
    for s in schedules:
        try:
            k_id = int(s.kit_id)
        except (ValueError, TypeError):
            k_id = s.kit_id
        s.kit_obj = kit_map.get(k_id)
        s.user_obj = user_map.get(s.user_id)
        s_start = s.start if timezone.is_aware(s.start) else timezone.make_aware(s.start)
        s_end = s.end if timezone.is_aware(s.end) else timezone.make_aware(s.end)
        s.is_active = (s_start <= now <= s_end)
        s.is_upcoming = (s_start > now)
        s.is_past = (s_end < now)
        enriched_schedules.append(s)

    stats = {
        "total_kits": len(enriched_kits),
        "ready_kits": sum(1 for k in enriched_kits if k.is_ready),
        "total_instruments": len(instruments),
        "working_instruments": sum(1 for i in instruments if i.working),
        "faulty_instruments": sum(1 for i in instruments if not i.working),
        "total_users": len(users),
        "total_bookings": len(schedules),
        "active_bookings": sum(1 for s in enriched_schedules if s.is_active or s.is_upcoming),
    }

    return render(request, "main.html", {
        "users": users,
        "instruments": instruments,
        "kits": enriched_kits,
        "schedules": enriched_schedules,
        "stats": stats,
        "ans": ans,
        "status_type": status_type,
        "active_tab": active_tab,
        "inspected_kit_id": int(request.POST.get("kit_id", 0)) if request.POST.get("action") == "check_kit" and request.POST.get("kit_id", "").isdigit() else None
    })
