from PyQt5.QtGui import QIcon

import os
import re
import json
import mobase


class GamePluginsRequirement(mobase.IPluginRequirement):

    def __init__(self):
        super().__init__()

    def check(self, organizer: mobase.IOrganizer):
        managedGame = organizer.managedGame()
        if (managedGame and not managedGame.feature(mobase.GamePlugins)):
            return mobase.IPluginRequirement.Problem(
                "This plugin can only be enabled for games with plugins.")

        return None


class Plugin(mobase.IPluginTool):
    _modList: mobase.IModList
    _pluginList: mobase.IPluginList
    
    _dict = {}
    _mtime = None

    @classmethod
    def static_init(cls, organizer, json_file):
        cls._modList = organizer.modList()
        cls._pluginList = organizer.pluginList()

        # get the modlist.txt path, where the plugin_priority.json should be.
        p = organizer.getPluginDataPath()

        cls.json_path = os.path.join(p, os.pardir, "plugin_sync", json_file)
        cls.update_json(organizer)

    @classmethod
    def update_json(cls, organizer):
        mtime = os.path.getmtime(cls.json_path)
        if mtime is not cls._mtime:
            cls._mtime = mtime
            with open(cls.json_path) as file:
                cls._dict = json.load(file)

    @classmethod
    def getMasters(cls):
        return cls._dict["masters"]

    @classmethod
    def getPriority(cls, name, origin_fun):
        priority = cls._modList.priority(origin_fun(name))
        if name in cls._dict["delinquent"]:
            inc = 0.0
            l = cls._dict["delinquent"][name]
            for plugin in [l] if isinstance(l, str) else l:
                inc += 0.0000001
                alt = Plugin.getPriority(plugin, origin_fun)
                priority = max(priority, alt + inc)
        return priority

    def __init__(self, pluginName, origin_fun):
        self.pluginName = pluginName
        self.modname = origin_fun(pluginName)
        self.priority = Plugin.getPriority(pluginName, origin_fun)

    def __lt__(self, other):
        name = self.pluginName
        oName = other.pluginName

        if self.priority != other.priority:
            for mod in self._dict["bottomMods"]:
                if mod is name:
                    return False
                if mod is oName:
                    return True
            return self.priority < other.priority

        return oName not in self._pluginList.masters(name)


class PluginSync(mobase.IPluginTool):

    _organizer: mobase.IOrganizer
    _pluginList: mobase.IPluginList

    def __init__(self):
        super().__init__()

    def init(self, organizer: mobase.IOrganizer):
        self._organizer = organizer
        self._pluginList = organizer.pluginList()
        Plugin.static_init(organizer, "plugin_priority.json")
        return True

    def name(self):
        return "Sync Plugins"

    def author(self):
        return "coldrifting"

    def description(self):
        return "Syncs plugin load order with mod order"

    def version(self):
        return mobase.VersionInfo(1, 0, 0, mobase.ReleaseType.FINAL)

    def isActive(self):
        return (self._organizer.managedGame().feature(mobase.GamePlugins))

    def settings(self):
        return []

    def display(self):
        # Get all plugins as a list
        allPlugins = self._pluginList.pluginNames()

        #if json was edited in th mean time, reload.
        Plugin.update_json(self._organizer)

        # Sort the list by plugin origin
        allPlugins = sorted(
            allPlugins,
            key=lambda
            plugin: Plugin(plugin, self._pluginList.origin)
        )
        
        # Sort the list by dependencies
        # allPlugins = sorted(
        #     allPlugins,
        #     key=lambda
        #     
        # )

        # Split into two lists, master files and regular plugins
        plugins = []
        masters = Plugin.getMasters()
        for plugin in allPlugins:
            if plugin not in masters:
                if self._pluginList.isMaster(plugin):
                    masters.append(plugin)
                else:
                    plugins.append(plugin)

        # Merge masters into the plugin list at the begining
        allPlugins = masters + plugins

        # Set load order
        self._pluginList.setLoadOrder(allPlugins)

        # Update the plugin list to use the new load order
        self._organizer.managedGame().feature(
            mobase.GamePlugins).writePluginLists(self._pluginList)

        # Refresh the UI
        self._organizer.refresh()

        return True

    def displayName(self):
        return "Sync Plugins"

    def tooltip(self):
        return "Enables all Mods one at a time to match load order"

    def icon(self):
        return QIcon()

    def requirements(self):
        return [GamePluginsRequirement()]


def createPlugin() -> mobase.IPluginTool:
    return PluginSync()
