//
// Created by boris on 9/15/22.
//

#ifndef SCALA_DEMO_TWOATTHETIMECROSSINGSTRATEGY_H
#define SCALA_DEMO_TWOATTHETIMECROSSINGSTRATEGY_H

#include "CrossingStrategy.h"

class TwoAtTheTimeCrossingStrategy : public CrossingStrategy
{
public:
    TwoAtTheTimeCrossingStrategy()  {}
    float CalculateCrossing(std::shared_ptr<Crossing>) override;
};


#endif //SCALA_DEMO_TWOATTHETIMECROSSINGSTRATEGY_H
