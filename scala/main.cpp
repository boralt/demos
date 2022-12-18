#include <iostream>
#include <strstream>
#include "yaml-cpp/yaml.h"
#include "HikingScenario.h"
#include "TwoAtTheTimeCrossingStrategy.h"


std::string sYaml = R"EOF(
base-group:
  - speed: 10
  - speed: 12
crossings:
  - length: 100
    group:
      - speed: 3
      - speed: 6
  - length: 200
    group:
      - speed: 8
      - speed: 9

)EOF";


void process_group(YAML::Node config)
{
    auto i = 0;
    std::cout << "Hello Group size= " << config.size() << " \n";
    std::cout << "First " << config[0]["speed"].as<int>() << "\n";
    std::cout << "Second " << config[1]["speed"].as<int>() << "\n";
    for (YAML::const_iterator it=config.begin();it!=config.end();++it) {
        std::cout << "Iterator gave " << it->first << "\n";
    }
}

void process_bridges(YAML::Node config)
{
    auto i = 0;
    std::cout << "Hello Bridges size= " << config.size() << " \n";
    std::cout << "First len " << config[0]["length"] << "\n";
    process_group(config[0]["group"]);
    std::cout << "Second len " << config[1]["length"] << "\n";
    process_group(config[1]["group"]);
}


void process_node(YAML::Node config )
{
    for (YAML::const_iterator it=config.begin();it!=config.end();++it) {

        /*
        if(it->IsMap())
        {
            std::cout << "Map";
        }
        else if (it->IsScalar())
        {
            std::cout << "Scalar";
        }
        else if (it->IsSequence())
        {
            std::cout << "Seq";
        }
        else
        {
            std::cout << "Unknown";
        }
         */
        std::cout << ""  << ":" << it->first.as<std::string>() << "\n";
        if (it->first.as<std::string>() == "base-group")
            process_group(it->second);
        else if (it->first.as<std::string>() == "crossings")
            process_bridges(it->second);

    }

/*
    if (config["base-group"])
    {
        process_group(config["base_group"]);
    }
*/



}

#if 0

int main() {
    std::cout << "Hello, World!" << std::endl;
    YAML::Node config = YAML::Load(sYaml);
    process_node(config);



    return 0;
}

#endif

# if 1

int main(int argc, char **argv) {

    if (argc == 1)
    {
        std::cout << "Provide name of input file in YAML format" << std::endl;
        return 1;
    }
    else if (argc > 2)
    {
        std::cout << "Provide single parameter  file in YAML format" << std::endl;
        return 1;
    }

    HikingScenario scenario;

    scenario.LoadYamlFile(argv[1]);
    TwoAtTheTimeCrossingStrategy strategy;
    auto res = scenario.Run(strategy);

    std::cout << "Total time is " << res.total_time << std::endl << "Individual crossing times:" << std::endl;
    int index = 0;
    for (auto crossing_time: res.crossing_times)
    {
        std::cout << " " << crossing_time << " ";
    }
    std::cout << std::endl;
    return 0;
}
#endif
