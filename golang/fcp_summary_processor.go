 package snc

import (
    "bytes"
    "encoding/binary"
    "fmt"
    "net"
    "strconv"
)

type PrefixType struct {
    Base      uint32
    PrefixLen int
}

func ip2Long(ip net.IP) uint32 {
    var long uint32
    binary.Read(bytes.NewBuffer(ip.To4()), binary.BigEndian, &long)
    return long
}

func ipstr2Long(ip string) uint32 {
    return ip2Long(net.ParseIP(ip))
}

func MakePrefixFromString(s string) PrefixType {
    ip, ipNet, _ := net.ParseCIDR(s)
    sz, _ := ipNet.Mask.Size()
    return PrefixType{ip2Long(ip), sz}
}

func MakePrefix(ip string, prefix_len int) PrefixType {
    prefix := PrefixType{0, prefix_len}
    binary.Read(bytes.NewBuffer(net.ParseIP(ip).To4()), binary.BigEndian, &prefix.Base)
    return prefix
}

func (p PrefixType) String() string {
    b0 := strconv.Itoa(int((p.Base >> 24) & 0xff))
    b1 := strconv.Itoa(int((p.Base >> 16) & 0xff))
    b2 := strconv.Itoa(int((p.Base >> 8) & 0xff))
    b3 := strconv.Itoa(int(p.Base & 0xff))
    l := strconv.Itoa(p.PrefixLen)
    return b0 + "." + b1 + "." + b2 + "." + b3 + "/" + l
}

func (p PrefixType) OcPrefix() string {

    sIp := strconv.Itoa(int((p.Base>>24)&0xff)) + "." + strconv.Itoa(int((p.Base>>16)&0xff)) +
        "." + strconv.Itoa(int((p.Base>>8)&0xff)) + "." + strconv.Itoa(int(p.Base&0xff))
    res := fmt.Sprintf("%s/%d", sIp, p.PrefixLen)
    return res
}

type SummaryAggregatorType struct {
    // Route len that are checked against   Example 24
    InputPrefixLen int
    // Route len of potential summary       Example 22
    SummaryPrefixLen int

    // Example 192.168.1.0/24 = 0xC0A80100  ?? maybe don't need
    BaseInput uint32
    // Example for /24 = 0xFFFFFF00
    MaskInput uint32

    // Example for 192.168.1.0/23 = 0xC0A80000
    BaseSummary uint32
    // Example for /23 = 0xFFFFFC00
    MaskSummary uint32

    // part that should be completely aggrgated. Example for [/24 /23] 0x000003
    MaskAggregating uint32

    // Current progress in aggrgating. Success MaskAggregating == CurrentAggregating
    CurrentAggregating []bool
}

func MakeSummaryAggregator(inputPrefixLen int, summaryPrefixLen int) *SummaryAggregatorType {
    res := new(SummaryAggregatorType)
    res.InputPrefixLen = inputPrefixLen
    res.SummaryPrefixLen = summaryPrefixLen
    res.BaseInput = 0 // will be filled up later
    res.MaskInput = ^(1<<(uint)(32-inputPrefixLen) - 1)
    res.BaseSummary = 0 // will be filled up later
    res.MaskSummary = ^(1<<(uint)(32-summaryPrefixLen) - 1)
    res.MaskAggregating = res.MaskInput & ^res.MaskSummary
    res.CurrentAggregating = make([]bool, 1<<(uint)(res.InputPrefixLen-res.SummaryPrefixLen))
    return res
}

// this produces next level aggregator if previous level is satisfied
// or just copies input aggregator if it doesn't
func AdvanceSummaryAggregator(inputAggr *SummaryAggregatorType) *SummaryAggregatorType {

    if inputAggr.IsCompleted() {
        res := MakeSummaryAggregator(inputAggr.SummaryPrefixLen, inputAggr.SummaryPrefixLen-1)
        res.Add(inputAggr.MakeSummaryPrefix())
        return res
    }

    // no completed, return as is
    return inputAggr
}

func (s *SummaryAggregatorType) IsCompleted() bool {
    for _, completed := range s.CurrentAggregating {
        if !completed {
            return false
        }
    }
    return true
}

func (s *SummaryAggregatorType) IsMatchingPrefix(Prefix PrefixType) bool {
    if s.BaseInput == 0 {
        return true
    }
    if Prefix.PrefixLen != s.InputPrefixLen {
        return false
    }
    if (Prefix.Base & s.MaskSummary) == s.BaseSummary {
        return true
    }
    return false
}

func (myPrefix *SummaryAggregatorType) IsMatchingSummary(Prefix *SummaryAggregatorType) bool {
    if myPrefix.SummaryPrefixLen > Prefix.InputPrefixLen {
        return false
    }

    if (Prefix.BaseInput & myPrefix.MaskSummary) == myPrefix.BaseSummary {
        return true
    }
    return false
}

func (s *SummaryAggregatorType) Add(Prefix PrefixType) bool {
    if s.BaseInput == 0 {
        // complete configuration
        s.BaseSummary = Prefix.Base & s.MaskSummary
        s.BaseInput = Prefix.Base & s.MaskInput // Probably is not needed
    }

    // fillup this level
    s.CurrentAggregating[(Prefix.Base&s.MaskAggregating)>>(uint)(32-s.InputPrefixLen)] = true
    return true
}

func (s *SummaryAggregatorType) MakeSummaryPrefix() PrefixType {
    res := PrefixType{0, 0}

    // completed level, generate next prefix
    res.PrefixLen = s.SummaryPrefixLen
    res.Base = s.BaseSummary
    return res
}

func (s *SummaryAggregatorType) FetchPrefixes(fetchInto []PrefixType) []PrefixType {
    if s.IsCompleted() {
        fetchInto = append(fetchInto, s.MakeSummaryPrefix())
    } else {
        for presentIndex, completed := range s.CurrentAggregating {
            if completed {
                basePrefix := s.BaseSummary + (uint32(presentIndex) << (uint)(32-s.InputPrefixLen))
                generatedPrefix := PrefixType{basePrefix, s.InputPrefixLen}
                fetchInto = append(fetchInto, generatedPrefix)
            }
        }
    }
    return fetchInto
}

//===================  Generate summary ===================

// recursive function
//generates reduced list of aggregators by summarizing
func CollapsePrefixAggregators(aggregatorsIn []*SummaryAggregatorType) []*SummaryAggregatorType {
    // maximum size
    arAggregatorsRes := make([]*SummaryAggregatorType, len(aggregatorsIn))

    countResult := 0
    for _, inpAggregator := range aggregatorsIn {
        for testIndex, testAggr := range arAggregatorsRes {
            if testAggr == nil {
                // create new aggregator as nothing else matched
                arAggregatorsRes[testIndex] =
                    AdvanceSummaryAggregator(inpAggregator)
                countResult = testIndex + 1
                break
            } else if testAggr.IsMatchingSummary(inpAggregator) {
                // summarize on this level
                tmpPrefixes := []PrefixType{}
                tmpPrefixes = inpAggregator.FetchPrefixes(tmpPrefixes)
                for _, p := range tmpPrefixes {
                    testAggr.Add(p)
                }
                //testAggr.Add(inpAggregator.MakeSummaryPrefix())
                break
            }
        }
    }

    if len(aggregatorsIn) <= countResult {
        // nothing summarixed on this level  -- we are done
        return arAggregatorsRes[0:countResult]
    }

    // iterate some more
    return CollapsePrefixAggregators(arAggregatorsRes[0:countResult])
}

func CalcSummary(Prefixes []PrefixType) []PrefixType {
    arAggregatorsIn := make([]*SummaryAggregatorType, len(Prefixes))
    // Create 1:1 list of Summary aggregators and enter recursion
    for i, prefix := range Prefixes {
        arAggregatorsIn[i] = MakeSummaryAggregator(prefix.PrefixLen, prefix.PrefixLen)
        arAggregatorsIn[i].Add(prefix)
    }

    resultAggregators := CollapsePrefixAggregators(arAggregatorsIn)
    // produce list of prefixes
    res := []PrefixType{}
    // scan all summaries in pull prefixes
    for _, aggregator := range resultAggregators {
        res = aggregator.FetchPrefixes(res)
    }
    return res
}

type SummaryProcessorType struct {
    PrefixLen int
    Summaries []SummaryAggregatorType
}
