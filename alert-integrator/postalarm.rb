#!/usr/bin/env ruby

require "./alarmintegrator"

class FileCorruptionAlert < AlertItem

    def initialize 
        @impact_levels = ["none", "ha_lower", "service_down"]
        @data = ""
        @timestamp = nil
        @filename = ""
        @pod = ""
        @filetype = ""
        @key = ""
        @impact = ""
    end

    attr_accessor :impact_levels
    attr_accessor :data
    attr_accessor :timestamp
    attr_accessor :filename
    attr_accessor :pod
    attr_accessor :filetype
    attr_accessor :key
    attr_accessor :impact

    def to_tag
        @timestamp = Time.now
        data_point = {"data" => @data, "timestamp" => @timestamp.gmtime}
        attributes = {"filename" => @filename,
                      "pod" => @pod,
                      "filetype" => @filetype,
                      "key" => @key,
                      "impact" => @impact,
                      "problem" => "corruption"}
        tag = {"tagname" => "fci/pod_health", "datapoints" => [data_point], "attributes" => attributes}
        return tag
    end

    def from_tag(tag)
        @data = tag["data"]
        @timestamp = time.parse(tag["timestamp"])
        @attributes = tag["attributes"]
        @filename = attributes.fetch("filename", "")
        self.pod = attributes.fetch("pod", "")
        self.filetype = attributes.fetch("filetype", "none")
        self.key = attributes.fetch("key", "")
        self.impact = attributes.fetch("impact", "")
    end

    def is_same_type(another)
        return False
    end

    def clear_alert
        @impact = @impact_levels[0]
    end

    def is_cleared?
        return @impact == @impact_levels[0]
    end

    def self.alert_filter
        return {"is_regex" => true, "tagname" => "fci/pod_health"}
    end
end

puts "Doing send"
prefix = "x"
state = "SET"

prefix = ARGV[2] if ARGV.length > 2
state = ARGV[3] if ARGV.length > 3

ai = AlertIntegrator.new(FileCorruptionAlert, "192.168.8.162:9093")
alert = FileCorruptionAlert.new
alert.pod = "pod-" + prefix
alert.impact = "service_down"
alert.filetype = "hint"
alert.filename = "f-" + prefix
alert.data = 1
ai.add_active_alert(alert)
ai.update_tms_alerts()




