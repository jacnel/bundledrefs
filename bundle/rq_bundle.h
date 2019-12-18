#ifndef BUNDLE_RQ_BUNDLE_H
#define BUNDLE_RQ_BUNDLE_H

#if (BUNDLE_BUNDLE_TYPE == BUNDLE_CIRCULAR) 
#include "circular_bundle.h"
#elif (BUNDLE_BUNDLE_TYPE == BUNDLE_LINKED) 
#include "linked_bundle.h"
#endif

#endif