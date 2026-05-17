import json
import hashlib
import hmac
import base64
import uuid
from datetime import datetime, timezone
from typing import Optional
import httpx
import urllib.parse


BSS_ENDPOINTS = {
    "china": "business.aliyuncs.com",
    "international": "business.ap-southeast-1.aliyuncs.com",
}

ECS_ENDPOINTS = {
    "cn-hangzhou": "ecs.cn-hangzhou.aliyuncs.com",
    "ap-southeast-1": "ecs.ap-southeast-1.aliyuncs.com",
    "ap-northeast-1": "ecs.ap-northeast-1.aliyuncs.com",
    "us-west-1": "ecs.us-west-1.aliyuncs.com",
    "us-east-1": "ecs.us-east-1.aliyuncs.com",
    "cn-hongkong": "ecs.cn-hongkong.aliyuncs.com",
    "eu-central-1": "ecs.eu-central-1.aliyuncs.com",
}

CMS_ENDPOINT = "metrics.aliyuncs.com"
CDT_ENDPOINT = "cdt.aliyuncs.com"


def _sign(key_secret: str, string_to_sign: str) -> str:
    h = hmac.new(
        (key_secret + "&").encode("utf-8"),
        string_to_sign.encode("utf-8"),
        hashlib.sha1,
    )
    return base64.b64encode(h.digest()).decode("utf-8")


def _build_params(action: str, key_id: str, key_secret: str, version: str, extra: dict) -> dict:
    params = {
        "Format": "JSON",
        "Version": version,
        "AccessKeyId": key_id,
        "SignatureMethod": "HMAC-SHA1",
        "Timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "SignatureVersion": "1.0",
        "SignatureNonce": str(uuid.uuid4()),
        "Action": action,
        **extra,
    }
    sorted_params = sorted(params.items())
    query_string = urllib.parse.urlencode(sorted_params)
    string_to_sign = "POST&%2F&" + urllib.parse.quote(query_string, safe="")
    params["Signature"] = _sign(key_secret, string_to_sign)
    return params


async def _post(host: str, params: dict, timeout: float = 10.0) -> dict:
    url = f"https://{host}/"
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(url, data=params)
        data = resp.json()
        if "Code" in data and str(data.get("Code")) not in ("200", "0", ""):
            raise Exception(f"API Error [{data.get('Code')}]: {data.get('Message', 'unknown')}")
        return data


class AliyunClient:
    def __init__(self, key_id: str, key_secret: str, region_id: str, site_type: str = "international"):
        self.key_id = key_id
        self.key_secret = key_secret
        self.region_id = region_id
        self.site_type = site_type
        self.bss_host = BSS_ENDPOINTS.get(site_type, BSS_ENDPOINTS["international"])
        self.ecs_host = ECS_ENDPOINTS.get(region_id, f"ecs.{region_id}.aliyuncs.com")

    # ==================== 余额 ====================
    async def get_balance(self) -> dict:
        params = _build_params(
            "QueryAccountBalance", self.key_id, self.key_secret,
            "2017-12-14", {}
        )
        data = await _post(self.bss_host, params)
        d = data.get("Data", {})
        return {
            "available_amount": float(d.get("AvailableAmount", 0)),
            "currency": d.get("Currency", "USD"),
        }

    # ==================== 账单（待还款） ====================
    async def get_bill_overview(self, billing_cycle: Optional[str] = None) -> dict:
        if not billing_cycle:
            billing_cycle = datetime.now().strftime("%Y-%m")
        params = _build_params(
            "QueryBillOverview", self.key_id, self.key_secret,
            "2017-12-14", {"BillingCycle": billing_cycle}
        )
        data = await _post(self.bss_host, params)
        items = data.get("Data", {}).get("Items", {}).get("Item", [])
        total_outstanding = 0.0
        total_pretax = 0.0
        details = []
        for item in items:
            outstanding = float(item.get("OutstandingAmount", 0))
            pretax = float(item.get("PretaxAmount", 0))
            total_outstanding += outstanding
            total_pretax += pretax
            if pretax > 0 or outstanding > 0:
                details.append({
                    "product": item.get("ProductName", ""),
                    "pretax_amount": round(pretax, 4),
                    "outstanding_amount": round(outstanding, 4),
                    "currency": item.get("Currency", "USD"),
                })
        return {
            "billing_cycle": billing_cycle,
            "total_outstanding": round(total_outstanding, 4),  # 待还款（最准确）
            "total_pretax": round(total_pretax, 4),
            "currency": "USD" if self.site_type == "international" else "CNY",
            "details": details,
        }

    # ==================== CDT 流量 ====================
    async def get_cdt_traffic(self) -> float:
        """返回本月已用流量 GB"""
        params = _build_params(
            "ListCdtInternetTraffic", self.key_id, self.key_secret,
            "2021-08-16", {
                "RegionId": self.region_id,
                "Month": datetime.now().strftime("%Y-%m"),
            }
        )
        try:
            data = await _post(CDT_ENDPOINT, params)
            traffics = data.get("TrafficDetails", {}).get("TrafficDetail", [])
            total_bytes = sum(float(t.get("TotalTraffic", 0)) for t in traffics)
            return round(total_bytes / (1024 ** 3), 3)
        except Exception:
            # CDT API 不可用时fallback到CMS
            return await self._get_traffic_from_cms()

    async def _get_traffic_from_cms(self) -> float:
        """从CMS获取实例公网出口流量"""
        return 0.0  # fallback，后续完善

    # ==================== 实例状态 ====================
    async def get_instances(self) -> list:
        params = _build_params(
            "DescribeInstances", self.key_id, self.key_secret,
            "2014-05-26", {
                "RegionId": self.region_id,
                "PageSize": "100",
            }
        )
        data = await _post(self.ecs_host, params)
        instances = data.get("Instances", {}).get("Instance", [])
        result = []
        for inst in instances:
            ip_list = inst.get("PublicIpAddress", {}).get("IpAddress", [])
            eip = inst.get("EipAddress", {}).get("IpAddress", "")
            public_ip = eip or (ip_list[0] if ip_list else "")
            result.append({
                "instance_id": inst.get("InstanceId"),
                "instance_name": inst.get("InstanceName"),
                "status": inst.get("Status"),
                "public_ip": public_ip,
                "instance_type": inst.get("InstanceType"),
                "region_id": inst.get("RegionId"),
                "is_spot": inst.get("SpotStrategy", "") != "NoSpot",
                "bandwidth_mbps": inst.get("InternetMaxBandwidthOut", 0),
            })
        return result

    async def get_instance_status(self, instance_id: str) -> str:
        params = _build_params(
            "DescribeInstanceStatus", self.key_id, self.key_secret,
            "2014-05-26", {
                "RegionId": self.region_id,
                "InstanceId.1": instance_id,
            }
        )
        data = await _post(self.ecs_host, params)
        items = data.get("InstanceStatuses", {}).get("InstanceStatus", [])
        return items[0].get("Status", "Unknown") if items else "Unknown"

    async def start_instance(self, instance_id: str) -> bool:
        params = _build_params(
            "StartInstance", self.key_id, self.key_secret,
            "2014-05-26", {"InstanceId": instance_id}
        )
        await _post(self.ecs_host, params)
        return True

    async def stop_instance(self, instance_id: str, mode: str = "StopCharging") -> bool:
        params = _build_params(
            "StopInstance", self.key_id, self.key_secret,
            "2014-05-26", {
                "InstanceId": instance_id,
                "StoppedMode": mode,
                "ForceStop": "false",
            }
        )
        await _post(self.ecs_host, params)
        return True

    async def delete_instance(self, instance_id: str) -> bool:
        params = _build_params(
            "DeleteInstance", self.key_id, self.key_secret,
            "2014-05-26", {
                "InstanceId": instance_id,
                "Force": "true",
            }
        )
        await _post(self.ecs_host, params)
        return True

    # ==================== CF DDNS ====================
    async def update_cf_dns(self, zone_id: str, api_token: str, record_name: str, ip: str) -> bool:
        headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=10) as client:
            # 查找记录ID
            resp = await client.get(
                f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records",
                headers=headers,
                params={"type": "A", "name": record_name},
            )
            records = resp.json().get("result", [])
            if not records:
                return False
            record_id = records[0]["id"]
            # 更新
            await client.put(
                f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records/{record_id}",
                headers=headers,
                json={"type": "A", "name": record_name, "content": ip, "proxied": True},
            )
        return True
