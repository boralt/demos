//
// Created by Boris Altshul on 9/14/22.
//

#include <gtest/gtest.h>
#include "yaml-cpp/yaml.h"
#include "../HikingScenario.h"
#include "../TwoAtTheTimeCrossingStrategy.h"


TEST(SimpleWalk, BasicAssertions) {
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

    HikingScenario scenario;
    scenario.LoadYamlString(sYaml.c_str());
    TwoAtTheTimeCrossingStrategy strategy;
    auto res = scenario.Run(strategy);

    EXPECT_NEAR(res.crossing_times[0], 77.,1);
    EXPECT_NEAR(res.crossing_times[1], 100., 1);
    EXPECT_NEAR(res.total_time, 177., 1);

}


TEST(QuickWaitingWalk, BasicAssertions) {
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
      - speed: 100
      - speed: 9

)EOF";

    HikingScenario scenario;
    scenario.LoadYamlString(sYaml.c_str());
    TwoAtTheTimeCrossingStrategy strategy;
    auto res = scenario.Run(strategy);

    EXPECT_NEAR(res.crossing_times[0], 77.,1);
    EXPECT_NEAR(res.crossing_times[1], 63., 1);
    EXPECT_NEAR(res.total_time, 140., 1);

}


TEST(EmptyCrossing, BasicAssertions) {
    std::string sYaml = R"EOF(
base-group:
  - speed: 10
  - speed: 12
crossings:
  - length: 100
    group:
  - length: 200
    group:
      - speed: 8
      - speed: 9

)EOF";

    HikingScenario scenario;
    scenario.LoadYamlString(sYaml.c_str());
    TwoAtTheTimeCrossingStrategy strategy;
    auto res = scenario.Run(strategy);

    EXPECT_NEAR(res.crossing_times[0], 10.,1) << "Got " << res.crossing_times[0] ;
    EXPECT_NEAR(res.crossing_times[1], 100., 1) << "Got " << res.crossing_times[1];
    EXPECT_NEAR(res.total_time, 110., 1) << "Got " << res.total_time;

}

TEST(SingleWalker, BasicAssertions) {
    std::string sYaml = R"EOF(
base-group:
  - speed: 10
crossings:
  - length: 100
  - length: 200
    group:
  )EOF";

    HikingScenario scenario;
    scenario.LoadYamlString(sYaml.c_str());
    TwoAtTheTimeCrossingStrategy strategy;
    auto res = scenario.Run(strategy);

    EXPECT_NEAR(res.crossing_times[0], 10.,1) << "Got " << res.crossing_times[0] ;
    EXPECT_NEAR(res.crossing_times[1], 20., 1) << "Got " << res.crossing_times[1];
    EXPECT_NEAR(res.total_time, 30., 1) << "Got " << res.total_time;
}






