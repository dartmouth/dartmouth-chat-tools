"""
title: Time Utilities
version: 0.11.3
icon_url: Calendar
"""

import json
import logging

from fastapi import Request

log = logging.getLogger(__name__)


class Tools:
    async def get_current_timestamp(
        self,
        __request__: Request = None,
        __user__: dict = None,
    ) -> str:
        """
        Get the current Unix timestamp in seconds.

        :return: JSON with current_timestamp (seconds), current_iso (UTC ISO format), and user_local_iso (user's local time)
        """
        try:
            import datetime
            from zoneinfo import ZoneInfo

            now = datetime.datetime.now(datetime.timezone.utc)
            result = {
                'current_timestamp': int(now.timestamp()),
                'current_iso': now.isoformat(),
            }

            # Include the user's local time if timezone is available
            tz_name = __user__.get('timezone') if __user__ else None
            if tz_name:
                try:
                    user_tz = ZoneInfo(tz_name)
                    user_now = now.astimezone(user_tz)
                    result['user_local_iso'] = user_now.isoformat()
                    result['user_timezone'] = tz_name
                except Exception:
                    pass

            return json.dumps(result, ensure_ascii=False)
        except Exception as e:
            log.exception(f'get_current_timestamp error: {e}')
            return json.dumps({'error': str(e)})


    async def calculate_timestamp(
        self,
        days_ago: int = 0,
        weeks_ago: int = 0,
        months_ago: int = 0,
        years_ago: int = 0,
        __request__: Request = None,
        __user__: dict = None,
    ) -> str:
        """
        Get the current Unix timestamp, optionally adjusted by days, weeks, months, or years.
        Use this to calculate timestamps for date filtering in search functions.
        Examples: "last week" = weeks_ago=1, "3 days ago" = days_ago=3, "a year ago" = years_ago=1

        :param days_ago: Number of days to subtract from current time (default: 0)
        :param weeks_ago: Number of weeks to subtract from current time (default: 0)
        :param months_ago: Number of months to subtract from current time (default: 0)
        :param years_ago: Number of years to subtract from current time (default: 0)
        :return: JSON with current_timestamp and calculated_timestamp (both in seconds)
        """
        try:
            import datetime
            from dateutil.relativedelta import relativedelta

            now = datetime.datetime.now(datetime.timezone.utc)
            current_ts = int(now.timestamp())

            # Calculate the adjusted time
            total_days = days_ago + (weeks_ago * 7)
            adjusted = now - datetime.timedelta(days=total_days)

            # Handle months and years separately (variable length)
            if months_ago > 0 or years_ago > 0:
                adjusted = adjusted - relativedelta(months=months_ago, years=years_ago)

            adjusted_ts = int(adjusted.timestamp())

            result = {
                'current_timestamp': current_ts,
                'current_iso': now.isoformat(),
                'calculated_timestamp': adjusted_ts,
                'calculated_iso': adjusted.isoformat(),
            }

            # Include the user's local time if timezone is available
            tz_name = __user__.get('timezone') if __user__ else None
            if tz_name:
                try:
                    from zoneinfo import ZoneInfo

                    user_tz = ZoneInfo(tz_name)
                    result['user_local_iso'] = now.astimezone(user_tz).isoformat()
                    result['calculated_local_iso'] = adjusted.astimezone(user_tz).isoformat()
                    result['user_timezone'] = tz_name
                except Exception:
                    pass

            return json.dumps(result, ensure_ascii=False)
        except ImportError:
            # Fallback without dateutil
            import datetime

            now = datetime.datetime.now(datetime.timezone.utc)
            current_ts = int(now.timestamp())
            total_days = days_ago + (weeks_ago * 7) + (months_ago * 30) + (years_ago * 365)
            adjusted = now - datetime.timedelta(days=total_days)
            adjusted_ts = int(adjusted.timestamp())
            result = {
                'current_timestamp': current_ts,
                'current_iso': now.isoformat(),
                'calculated_timestamp': adjusted_ts,
                'calculated_iso': adjusted.isoformat(),
            }

            tz_name = __user__.get('timezone') if __user__ else None
            if tz_name:
                try:
                    from zoneinfo import ZoneInfo

                    user_tz = ZoneInfo(tz_name)
                    result['user_local_iso'] = now.astimezone(user_tz).isoformat()
                    result['calculated_local_iso'] = adjusted.astimezone(user_tz).isoformat()
                    result['user_timezone'] = tz_name
                except Exception:
                    pass

            return json.dumps(result, ensure_ascii=False)
        except Exception as e:
            log.exception(f'calculate_timestamp error: {e}')
            return json.dumps({'error': str(e)})
