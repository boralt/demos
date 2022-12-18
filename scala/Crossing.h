//
// Created by boris on 9/15/22.
//

#ifndef SCALA_DEMO_CROSSING_H
#define SCALA_DEMO_CROSSING_H
#include <memory>
#include "Bridge.h"
#include "TravelerGroup.h"


class Crossing {

public:
    Crossing();
    Crossing(std::shared_ptr<Bridge> _bridge, std::shared_ptr<TravelerGroup> _waitingGroup) :
        bridge(_bridge), waitingGroup(_waitingGroup) {}

    std::shared_ptr<Bridge> GetBridge() const {return bridge;}
    std::shared_ptr<TravelerGroup> GetWaitingGroup() const {return waitingGroup;}

protected:
    std::shared_ptr<Bridge> bridge;
    std::shared_ptr<TravelerGroup> waitingGroup;
};


#endif //SCALA_DEMO_CROSSING_H
