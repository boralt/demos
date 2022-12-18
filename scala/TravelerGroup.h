//
// Created by boris on 9/15/22.
//

#ifndef SCALA_DEMO_TRAVELERGROUP_H
#define SCALA_DEMO_TRAVELERGROUP_H

#include <memory>
#include <list>
#include "Traveler.h"

class TravelerGroup {
public:
    TravelerGroup() {};
    void AddTraveler(std::shared_ptr<Traveler> traveler) { travelers.push_back(traveler);}
    std::list<std::shared_ptr<Traveler> > GetTravelers() const { return travelers; }
protected:
    std::list<std::shared_ptr<Traveler> > travelers{};
};

#endif //SCALA_DEMO_TRAVELERGROUP_H
