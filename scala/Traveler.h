//
// Created by boris on 9/15/22.
//

#ifndef SCALA_DEMO_TRAVELER_H
#define SCALA_DEMO_TRAVELER_H

class Traveler {
public:
    Traveler(float _speed) : speed{_speed} {}
    auto GetSpeed() const {return speed;}
protected:
    float speed{};
};


#endif //SCALA_DEMO_TRAVELER_H
