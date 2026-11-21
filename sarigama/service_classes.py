import threading
from datetime import timedelta
from django.utils import timezone
from django.db import transaction
from . import models
import json

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

