from django.shortcuts import render
from django.http import HttpResponse
from datetime import timedelta
from . import models


class user:
    @staticmethod
    def register_user(name, age, number, adhar):
        models.user.objects.create(
            user_name=name,
            user_age=age,
            user_number=number,
            user_adhar=adhar
        )


class kit:
    @staticmethod
    def add_kit(cost, items):
        models.kit.objects.create(cost=cost, items=items)

    @staticmethod
    def remove_kit(id):
        models.kit.objects.filter(id=id).delete()


class item:
    @staticmethod
    def insert_item(name, brand):
        models.instrument.objects.create(
            instrument_name=name,
            brand=brand
        )

    @staticmethod
    def setdescreption(data, itemid):
        models.instrument.objects.filter(id=itemid).update(
            specifiations=data
        )


class allotment:
    min_gap = timedelta(minutes=15)
    min_time = timedelta(minutes=60)

    @staticmethod
    def allot_item(kit_id, start, end, userid):
        if start >= end or end - start < allotment.min_time:
            print("enter valid time period")
            return

        for i in models.schedule.objects.filter(kit_id=kit_id):
            if (
                start < i.end + allotment.min_gap
                and end > i.start - allotment.min_gap
            ):
                print("slot not available")
                return

        models.schedule.objects.create(
            kit_id=kit_id,
            user_id=userid,
            start=start,
            end=end
        )