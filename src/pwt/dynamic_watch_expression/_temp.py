import os
import re
import socket
import subprocess
from ipaddress import IPv4Address, IPv6Address, ip_address
from typing import Any, Generator, Iterable

import dns.resolver

from pwt.dynamic_watch_expression.miwifi import CodeError, MiWifi


class WatcherTask1:
    """
    该类负责执行监视器的任务, 包括执行fetches插件和评估expression和执行executes插件.
    """

    def __init__(self, watcher: Watcher, root_logger: logging.Logger) -> None:
        """
        初始化WatcherTask实例.

        参数:
            watcher: 包含监视器配置的Watcher对象.
            root_logger: 根日志记录器, 用于创建特定于监视器的子日志记录器.

        异常:
            UnexpectedInput: 表达式解析错误时, 将出现以下子异常之一:
                UnexpectedCharacters, UnexpectedToken, UnexpectedEOF
            ModuleNotFoundError: 如果插件模块未找到或插件类未定义.
        """

        self.logger = root_logger.getChild(watcher.name)
        self.logger.info(f"Initializing watcher task for '{watcher.name}'")
        self.logger.debug(f"WatcherTask configuration: {repr(watcher)}")
        self.name = watcher.name
        self.interval = watcher.interval
        self.tolerance = watcher.tolerance
        self.expression = Expression(watcher.expression)
        self.fetches = [
            PluginBase.create_plugin(**action.model_dump())
            for action in watcher.fetches
        ]
        self.executes = [
            PluginBase.create_plugin(**action.model_dump())
            for action in watcher.executes
        ]
        self.attempts = 0
        self.extra = {}
        self.logger.info(f"Initialized watcher task for '{self.name}'")
        self.logger.debug(f"WatcherTask configuration: {self}")

    def __call__(self) -> None:
        """
        执行监视器的任务.

        该方法首先执行所有的fetches插件, 然后评估表达式.
        如果表达式为False, 则重置尝试次数并返回.
        如果表达式为True且尝试次数小于容忍度, 则增加尝试次数并返回.
        如果达到容忍度, 该方法执行所有的executes插件.
        """

        self.logger.info(f"Starting watcher task for '{self.name}'")
        self.execute_plugins(self.fetches)
        if not self.evaluate_expression():
            self.attempts = 0
            self.logger.info(
                f"Expression evaluated to False for '{self.name}', resetting attempts"
            )
            return
        if self.attempts < self.tolerance:
            self.attempts += 1
            self.logger.info(
                f"Expression evaluated to True for '{self.name}', attempt {self.attempts} of {self.tolerance}"
            )
            return
        self.execute_plugins(self.executes)
        self.attempts = 0
        self.logger.info(f"Executed executes plugins for '{self.name}'")

    def execute_plugins(self, plugins: Iterable[PluginBase]):
        """
        执行给定的插件列表.

        参数:
            plugins: 要执行的插件列表.
        """

        self.logger.info(f"Starting execution of plugins for '{self.name}'")
        context = MappingProxyType(vars(self))
        for plugin in plugins:
            self.logger.debug(f"Executing plugin '{plugin.plugin}'")
            plugin.execute(context)
            if not plugin.assess_strategy():
                self.logger.info(
                    f"Plugin '{plugin.plugin}' failed assessment, stopping execution"
                )
                break
        self.extra = context.get("extra", {})
        self.logger.info(f"Finished execution of plugins for '{self.name}'")

    def evaluate_expression(self) -> bool:
        """
        评估表达式.

        返回:
            表达式的评估结果. 如果发生异常, 返回False.
        """

        self.logger.info(f"Starting evaluation of expression for '{self.name}'")
        variables = [plugin.result or [] for plugin in self.fetches]
        try:
            result = self.expression.evaluate(variables)
            self.logger.info(f"Expression evaluated to {result} for '{self.name}'")
            return result
        except Exception as e:
            self.logger.error(f"Error evaluating expression for '{self.name}': {e}")
            return False

    def __repr__(self) -> str:
        return str(vars(self))


class CommandOperate:
    """
    命令行插件
    """

    def __init__(
        self,
        cmd: str = "",
        dir: str | None = None,
        env: dict[str, str] | None = None,
        timeout: float | None = 30,
        encoding: str = "utf-8",
        regex: str = r"(.*)",
        ignorecase: bool = False,
    ) -> None:
        """
        初始化

        参数:
            cmd: 命令行
            dir: 起始路径
            env: 环境变量
            timeout: 超时时间(秒)
            encoding: 输出编码
            regex: 字符串提取正则表达式
            ignorecase: 正则表达式是否忽略大小写
        """

        self.args = cmd
        self.cwd = dir
        self.env = env
        if self.env:
            self.env = os.environ.copy().update(self.env)
        self.timeout = timeout
        self.encoding = encoding
        self.regex = regex
        self.ignorecase = ignorecase

    def __call__(self) -> list[IPv4Address | IPv6Address]:
        """
        获取地址列表

        返回:
            地址实例列表
        """

        addresses = []
        process = subprocess.run(
            args=self.args,
            cwd=self.cwd,
            env=self.env,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=self.timeout,
            check=True,
        )
        if self.encoding:
            result = process.stdout.decode(encoding=self.encoding)
        else:
            try:
                result = process.stdout.decode()
            except:
                result = process.stdout.decode(encoding="ansi")
        matched = re.findall(
            self.regex, result, re.IGNORECASE if self.ignorecase else 0
        )
        for address in _flatten(matched):
            _append_address(addresses, address)
        return addresses


class DnsOperate:
    """
    DNS插件
    """

    def __init__(self, domain: str = "", server: str = "") -> None:
        """
        初始化

        参数:
            domain: 域名
            server: 服务器
        """

        self.domain = domain
        self.server = server

    def __call__(self) -> list[IPv4Address | IPv6Address]:
        """
        获取地址列表

        返回:
            地址实例列表
        """

        if not self.domain:
            return []
        elif self.server:
            return self._get_addr_from_dns()
        else:
            return self._get_addr_from_socket()

    def _get_addr_from_socket(self) -> list[IPv4Address | IPv6Address]:
        addresses = []
        results = socket.getaddrinfo(self.domain, None, socket.AF_UNSPEC)
        for result in results:
            family, _, _, _, sockaddr = result
            address = sockaddr[0]
            if family == socket.AF_INET or family == socket.AF_INET6:
                _append_address(addresses, address)
        return addresses

    def _get_addr_from_dns(self) -> list[IPv4Address | IPv6Address]:
        addresses = []
        resolver = dns.resolver.Resolver()
        resolver.nameservers = re.split(r"[;,|\s]+", self.server)
        ipv4 = resolver.resolve(self.domain, "A", raise_on_no_answer=False)
        for address in iter(ipv4):
            _append_address(addresses, str(address))
        ipv6 = resolver.resolve(self.domain, "AAAA", raise_on_no_answer=False)
        for address in iter(ipv6):
            _append_address(addresses, str(address))
        return addresses


class MiWifiOperate:
    """
    小米路由插件
    """

    def __init__(self, host: str = "", password: str = "") -> None:
        """
        初始化

        参数:
            host: 地址, 默认: miwifi.com
            password: 密码
        """

        self.host = host
        self.password = password
        self._miwifi = MiWifi(self.host) if self.host else MiWifi()

    def __call__(self) -> list[IPv4Address | IPv6Address]:
        """
        获取地址列表

        返回:
            地址实例列表
        """

        addresses = []
        try:
            result = self._miwifi.get_wan_info()
        except CodeError as ex:
            if ex.code == 401:
                self._miwifi.login(self.password)
                result = self._miwifi.get_wan_info()
            else:
                raise
        try:
            ipv4 = result["info"]["ipv4"]
            for info in ipv4:
                address = info["ip"]
                _append_address(addresses, address)
        except:
            pass
        try:
            ipv6 = result["info"]["ipv6_info"]["ip6addr"]
            for info in ipv6:
                address = info["ip"]
                _append_address(addresses, address)
        except:
            pass
        return addresses


def _append_address(addresses: list[IPv4Address | IPv6Address], address: str) -> None:
    """
    转换为地址对象并插入到列表

    参数:
        addresses: 地址列表
        address: 地址字符串
    """

    try:
        addresses.append(ip_address(address))
    except:
        pass


def _flatten(data: Iterable) -> Generator[str, Any, None]:
    """
    展开嵌套可迭代实例

    参数:
        data: 可迭代实例
    返回:
        生成器, 内容为展开后的data内元素
    """

    for i in data:
        if isinstance(i, Iterable) and not isinstance(i, str):
            for j in _flatten(i):
                yield j
        else:
            yield i
