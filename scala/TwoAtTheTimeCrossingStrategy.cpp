//
// Created by boris on 9/15/22.
//

#include "Traveler.h"
#include "Crossing.h"
#include "TwoAtTheTimeCrossingStrategy.h"

float TwoAtTheTimeCrossingStrategy::CalculateCrossing(std::shared_ptr<Crossing> crossing)
{
    /*
     * This algorithm selects a fastest walker among all queueing at hte bridge
     * and let him walk back and force
     */

    auto secondary_group = crossing->GetWaitingGroup();
    auto bridge = crossing->GetBridge();
    float total_time = 0;

    // Find the fastest walker among all.
    // Assuming that member of waiting group can also be main walker
    std::shared_ptr<Traveler> fastest_walker;
    for(const auto walker : base_group->GetTravelers())
    {
        if (!fastest_walker || fastest_walker->GetSpeed() < walker->GetSpeed())
        {
            fastest_walker = walker;
        }
    }

    for(const auto walker:  secondary_group->GetTravelers())
    {
        if (!fastest_walker || fastest_walker->GetSpeed() < walker->GetSpeed())
        {
            fastest_walker = walker;
        }
    }

    if (!fastest_walker)
    {
        // Empty setup
        return 0;
    }

    // Start walking simulation and calculate total time
    // walk across with slower walker and return back
    // skip fastest walker

    // fastest walker on ingress side
    auto fastest_walker_crossed = false;

    for(const auto walker : base_group->GetTravelers())
    {
        if (fastest_walker != walker)
        {
            if (fastest_walker_crossed)
            {
                // waller needs to return to initial side
                total_time +=  static_cast<float>(bridge->GetLength())/ static_cast<float>(fastest_walker->GetSpeed());
            }
            // and now walk together with slow walker
            total_time += static_cast<float>(bridge->GetLength()) / static_cast<float>(walker->GetSpeed());
            fastest_walker_crossed = true;
        }
    }

    for(const auto walker:  secondary_group->GetTravelers())
    {
        if (fastest_walker != walker)
        {
            if (fastest_walker_crossed)
            {
                // walker needs to return to initial side
                total_time += static_cast<float>(bridge->GetLength()) / static_cast<float>(fastest_walker->GetSpeed());
            }
            // and now walk together with slow walker
            total_time += static_cast<float>(bridge->GetLength()) / static_cast<float>(walker->GetSpeed());
            fastest_walker_crossed = true;
        }
    }

    // If fastest walker still need to cross (lonely walker)
    if (!fastest_walker_crossed)
    {
        total_time += static_cast<float>(bridge->GetLength()) / static_cast<float>(fastest_walker->GetSpeed());
    }
    return total_time;
}
