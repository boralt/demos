//
// Created by boris on 9/15/22.
//

#ifndef SCALA_DEMO_BRIDGE_H
#define SCALA_DEMO_BRIDGE_H


class Bridge {
public:
    Bridge(float _length) : length{_length} {}
    auto GetLength() const { return length;}
protected:
    float length{};
};

#endif //SCALA_DEMO_BRIDGE_H
