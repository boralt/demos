//
// Created by boris on 9/15/22.
//

#ifndef SCALA_DEMO_CROSSINGSTRATEGY_H
#define SCALA_DEMO_CROSSINGSTRATEGY_H

#include "Crossing.h"

class CrossingStrategy {
public:

    void SetBaseGroup(std::shared_ptr<TravelerGroup> _group) { base_group = _group; }

    // returns best crossing time
    virtual float CalculateCrossing(std::shared_ptr<Crossing>) = 0;

protected:
    std::shared_ptr<TravelerGroup> base_group{};

};


#endif //SCALA_DEMO_CROSSINGSTRATEGY_H
