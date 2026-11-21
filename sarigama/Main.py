from django.shortcuts import render
from datetime import datetime
from django.utils import timezone
from django.db import models
from . import models
import json

from .Helpers import parse_kit_items
from .service_classes import user, kit, item, allotment, inspection



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
