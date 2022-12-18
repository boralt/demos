//
// Created by boris on 9/15/22.
//

#ifndef SCALA_DEMO_HIKINGSCENARIO_H
#define SCALA_DEMO_HIKINGSCENARIO_H

#include "yaml-cpp/yaml.h"
#include "TravelerGroup.h"
#include "Crossing.h"
#include "CrossingStrategy.h"

struct HikingScenarioResults
{
    float total_time{};
    std::vector<float> crossing_times{};
};

class HikingScenario {
public:
    void LoadYamlFile(const char *filename );
    void LoadYamlString(const char *data);

    // Apply bridge passing strategy
    HikingScenarioResults Run(CrossingStrategy &strategy);

protected:
    void Populate(YAML::Node config);

    static std::shared_ptr<TravelerGroup> LoadGroup(YAML::Node config);
    static std::shared_ptr<Crossing> LoadCrossing(YAML::Node config);

    std::shared_ptr<TravelerGroup> base_group{};
    std::list<std::shared_ptr<Crossing> > crossings{};
};



#endif //SCALA_DEMO_HIKINGSCENARIO_H
