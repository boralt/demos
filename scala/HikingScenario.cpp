//
// Created by boris on 9/15/22.
//

#include "HikingScenario.h"

std::shared_ptr<TravelerGroup> HikingScenario::LoadGroup(YAML::Node config)
{
    auto group = std::make_shared<TravelerGroup>();
    auto num_walkers = config.size();
    for (auto i=0; i < num_walkers; i++)
    {
        auto speed = config[i]["speed"].as<float>();
        group->AddTraveler( std::make_shared<Traveler>(speed));
    }
    return group;
}

std::shared_ptr<Crossing> HikingScenario::LoadCrossing(YAML::Node config)
{
    auto bridge_length = config["length"].as<float>();
    auto bridge = std::make_shared<Bridge>(bridge_length);
    auto waiting_travelers = LoadGroup(config["group"]);
    return std::make_shared<Crossing>(bridge, waiting_travelers);
}

void HikingScenario::Populate(YAML::Node config)
{
    for (YAML::const_iterator it=config.begin();it!=config.end();++it) {
        if (it->first.as<std::string>() == "base-group") {
            base_group = LoadGroup(it->second);
        }
        else if (it->first.as<std::string>() == "crossings") {
            YAML::Node crossing_node = it->second;
            auto num_crossings = crossing_node.size();
            for(auto i=0; i < num_crossings; i++) {
                auto crossing = LoadCrossing(crossing_node[i]);
                crossings.push_back(crossing);
            }
        }
    }
}

void HikingScenario::LoadYamlFile(const char *filename )
{
    YAML::Node config = YAML::LoadFile(filename);
    Populate(config);
}

void HikingScenario::LoadYamlString(const char *data)
{
    YAML::Node config = YAML::Load(data);
    Populate(config);
}


HikingScenarioResults HikingScenario::Run(CrossingStrategy &strategy)
{
    HikingScenarioResults res;

    strategy.SetBaseGroup(base_group);

    // Step through crossings one by one
    for (auto const crossing : crossings)
    {
        auto crossing_time = strategy.CalculateCrossing(crossing);
        res.total_time += crossing_time;
        res.crossing_times.push_back(crossing_time);
    }

    return res;
}

