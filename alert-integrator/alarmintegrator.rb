require "rdkafka"
require "json"

class AlertItem
    INTEG_UNRELATED = 1
    INTEG_REPLACE = 2
    INTEG_RETAIN = 3

    def initialize
    end


    def self.subscription_schema
        raise "Not implemented"
    end

    def self.alert_filter
        raise "Not Implemented"
    end

    def from_tag
        raise "Not implemented"
    end

    def is_same_type?(another)
        false
    end

    def is_cleared?(another)
        false
    end

    def integrate(another)
        unless is_same_type? another
            return INTEG_UNRELATED
        end
        return INTEG_RETAIN
    end

    def clear_alert
        raise "Not implemented"
    end
    
end

class AlertIntegrator

    RX_TOPIC = "alert_integrator"
    TOPIC_DATA = "TM_Default_Data_Topic_Request"
    TOPIC_CONTROL = "TM_Default_Ctrl_Topic_Request"
    GROUP_ID = "alarm-gr"


    def initialize( alert_class, kafka_bootstrap)
        @alert_class = alert_class
        @kafka_bootstrap = kafka_bootstrap
        # alerts posted into integrator
        @active_alerts = []
        #alerts_detected in tms 
        @current_alerts = []
    end

    def producer
        @producer ||= connect_producer
    end

    def consumer
        @consumer ||= connect_consumer
    end

    def connect_producer
        config = {  :"bootstrap.servers" => @kafka_bootstrap, 
                    :"message.max.bytes" => 2000000,
                    :"request.timeout.ms" => 15000,
                    :"retry.backoff.ms" => 1000,
                    :"retries" => 5,
                    :"request.required.acks" => "all"
        }
        producer = Rdkafka::Config.new(config).producer
        producer.delivery_callback = Proc.new { |delivery_report, delivery_handle| ack(delivery_report, delivery_handle) }
        return producer
    end

    def connect_consumer
        config = {  :"bootstrap.servers" => @kafka_bootstrap,
                    :"group.id" => GROUP_ID,
                    :"auto.offset.reset" => "smallest", 
                    :"auto.commit.interval.ms" => 1000
            
        }
        return Rdkafka::Config.new(config).consumer
    end

    def ack(delivery_report, delivery_handle)
        puts "Kafka delivered message with #{delivery_report}"
    end

    def receive_tms_alerts(topic, request_id)
        @current_alerts = []
        consumer.subsribe(topic)
        timeout = 5000
        while message = consumer.poll(timeout)
            timeout = 50
            message_hash = JSON.parse(message.payload)
            if message_hash["request_id"] == request_id
                message_hash["data"]["tags"].each do |datapoints|
                    datapoints.each do |datapoint| 
                        alert = @alert_class.new
                        alert.from_tag(datapoint)
                        @current_alerts << alert 
                    end

                end
            end
        end
        consumer.commit

    end

    def start_eventstream()
        evs_request = {}
        evs_request["request_id"] = (Time.now.to_f * 1000).to_i
        evs_request["request"] = "start_eventstream"
        evs_request["request_data"] = @alert_class.subscription_schema

        producer.produce(TOPIC_CONTROL, evs_request.to_json)
    end

    def stop_eventstream()
        evs_request = {}
        evs_request["request_id"] = (Time.now.to_f * 1000).to_i
        evs_request["request"] = "stop_eventstream"
        evs_request["request_data"] = {"eventstream_id" => @alert_class.subscription_schema["eventstream_id"]}

        producer.produce(TOPIC_CONTROL, evs_request.to_json)
    end


    def add_active_alert(alert)
        raise "Wrong alert type" unless alert.class == @alert_class
        @active_alerts << alert
    end

    def fetch_current_alerts
        query = @alert_class.alert_filter
        request_id = (Time.now.to_f * 1000).to_i
        req = {"request_id" => request_id, "request" => "query",
            "request_data" => {"tags" => [query]}, "response_topic" => RX_TOPIC }
        producer.produce(TOPIC_DATA, req.to_json)
        receive_tms_alerts(RX_TOPIC, request_id)
    end

    def prepare_update(alerts)
        tags = alerts.map {|alert| alert.to_tag}
        ingest_request = {}
        query = @alert_class.alert_filter
        ingest_cookie =  {"dpu" => "", "timestamp" => Time.now.gmtime.to_s, "tagname" => query["tagname"]}
        ingest_request["request_id"] = (Time.now.to_f * 1000).to_i
        ingest_request["request"] = "ingest"
        ingest_request["request_cookie"] = ingest_cookie
        ingest_request["request_data"] = {"tags" => tags}
        return ingest_request
    end

    def post_to_tmdata(req)
        producer.produce(topic: TOPIC_DATA, payload: req.to_json)
    end

    # integrate active alerts with current
    def update_tms_alerts
        alerts_to_post = []
        alerts_to_disable = []
        alerts_to_retain = []
        alerts_to_eval = @current_alerts.clone

        @active_alerts.each do |active_alert|
            matched = false
            @current_alerts.each do |current_alert|
                integ_action = active_alert.integrate(current_alert)
                if integ_action == AlertItem.INTEG_RETAIN
                    alerts_to_retain << active_alert
                    alerts_to_retain << current_alert
                    matched = true
                    break
                elsif integ_action == AlertItem.INTEG_UNRELATED
                    continue
                elsif integ_action == AlertItem.INTEG_REPLACE
                    alerts_to_post << active_alert
                    matched = true
                end
            end
            if not matched
                alerts_to_post << active_alert
            end
        end
        # remaining alerts not in retain list should be deleted
        @current_alerts.each do alert
            if alerts_to_retain.include? alert
                continue
            elsif alert.is_cleared()
                # already cleared alert. Nothing to do
                continue
            else
                alert.clear_alert()
                alerts_to_disable << alert
            end
        end
        # prepare update
        if alerts_to_disable or alerts_to_post
            req = prepare_update(alerts_to_eval + alerts_to_post)
            puts "Prepare to send #{req}"
            post_to_tmdata req 
        end
    end
end



