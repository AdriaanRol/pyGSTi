#*****************************************************************
#    pyGSTi 0.9:  Copyright 2015 Sandia Corporation              
#    This Software is released under the GPL license detailed    
#    in the file "license.txt" in the top-level pyGSTi directory 
#*****************************************************************
""" Defines the EvalTree class which implements an evaluation tree. """

import re as _re
import gatestring as _gs

class EvalTree(list):
    """
    An Evaluation Tree.  Instances of this class specify how to 
      perform bulk GateSet operations.

    EvalTree instances create and store the decomposition of a list
      of gate strings into a sequence of 2-term products of smaller
      strings.  Ideally, this sequence would prescribe the way to
      obtain the entire list of gate strings, starting with just the
      single gates, using the fewest number of multiplications, but
      this optimality is not guaranteed.
    """
    def __init__(self, items=[]):
        """ Create a new, empty, evaluation tree. """
        self.gateLabels = []
        self.finalList = []
        self.myFinalToParentFinalMap = []
        self.subTrees = []
        super(EvalTree, self).__init__(items)

    def initialize(self, gateLabels, gatestring_list):
        """
          Initialize an evaluation tree using a set of gate strings.
          This function must be called before using an EvalTree.

          Parameters
          ----------
          gateLabels : list of strings
              A list of all the single gate labels to 
              be stored at the beginnign of the tree.  This
              list must include all the gate labels contained
              in the elements of gatestring_list.

          gatestring_list : list of (tuples or GateStrings)
              A list of tuples of gate labels or GateString 
              objects, specifying the gate strings that
              should be present in the evaluation tree.

          Returns
          -------
          None
        """
        self.gateLabels = gateLabels

        if len(gatestring_list ) > 0 and isinstance(gatestring_list[0],_gs.GateString):
            gatestring_list = [gs.tup for gs in gatestring_list]

        #Evaluation dictionary:
        # keys == gate strings that have been evaluated so far
        # values == index of gate string (key) within evalTree
        evalDict = { } 

        #Evaluation tree:
        # A list of tuples, where each element contains
        #  information about evaluating a particular gate string:
        #  (iLeft, iRight, iInFinalList)
        # and the order of the elements specifies the evaluation order.
        # In particular, the gateString = evalTree[iLeft] + evalTree[iRight]
        #   so that matrix(gateString) = matrixOf(evalTree[iRight]) * matrixOf(evalTree[iLeft])
        #  and iInFinalList is the index of this gatestring in the gatestring_list
        # passed to this function, or -1 if it is not in the list.
        del self[:] #clear self (a list)

        #Final Index List
        # A list of integers whose i-th element is the index into evalTree
        #  corresponding to the i-th gatestring in gatestring_list.
        finalIndxList = [ None ] * len(gatestring_list)

        #Single gate (or zero-gate) computations are assumed to be atomic, and be computed independently.
        #  These labels serve as the initial values, and each gate string is assumed to be a tuple of gate labels.
        for gateLabel in self.gateLabels:
            if gateLabel == "": #special case of empty label == no gate
                evalDict[ () ] = len(self)
            else:
                evalDict[ (gateLabel,) ] = len(self)
            self.append( (None,None,-1) ) #iLeft = iRight = None for always-evaluated zero string
        
        #avgBiteSize = 0
        useCounts = {}
        for (k,gateString) in enumerate(gatestring_list):
            L = len(gateString)
            if L == 0: 
                self[0] = (None,None,k) #set in-final-list index for zero-length string (special case)
                finalIndxList[k] = 0

            start = 0; bite = 1
            #nBites = 0
            #print "DB: string = ",gateString, " tree length = ",len(self)

            while start < L:
                for b in xrange(L-start,0,-1):
                    if gateString[start:start+b] in evalDict: 
                        bite = b; break
                else: assert(False) #Logic error - loop above should always exit when b == 1

                #print "DB: start=", start, ": found ", gateString[start:start+bite], " in evalDict"
                iInFinal = k if bool(start + bite == L) else -1

                if start == 0: #first in-evalDict bite - no need to add anything to self yet
                    iCur = evalDict[ gateString[0:bite] ] 
                    if iInFinal >= 0:
                        if self[iCur][2] == -1: #set in-final-list index in existing tree node
                            self[iCur] = (self[iCur][0],self[iCur][1],iInFinal) 
                        finalIndxList[iInFinal] = iCur
                else:
                    assert(gateString[0:start+bite] not in evalDict)
                    iBite = evalDict[ gateString[start:start+bite] ]
                    iNew  = len(self)
                    evalDict[ gateString[0:start+bite] ] = iNew
                    self.append( (iCur,iBite,iInFinal) )
                    #print "DB: appending %s (index %d)" % (str(gateString[0:start+bite]),iNew)
                    if iInFinal >= 0: finalIndxList[iInFinal] = iNew
                    iCur = iNew
                start += bite
                #nBites += 1

            #if nBites > 0: avgBiteSize += L / float(nBites)

        #avgBiteSize /= float(len(gatestring_list))
        #print "DEBUG: Avg bite size = ",avgBiteSize
        
        #see if there are superfluous tree nodes: those with iFinal == -1 and 
        self.finalList = finalIndxList
        self.myFinalToParentFinalMap = [] #this tree has no "children", i.e. has not been created by a 'split'
        self.subTrees = [] #no subtrees yet

    def get_init_labels(self):
        """ Return a tuple of the gate labels (strings)
            which form the beginning of the tree.
        """
        return tuple(self.gateLabels)

    def get_tree_index_of_final_value(self, finalValueIndex):
        """ 
        Return the index within the tree list of the
          gate string that had index finalValueIndex in
          the gatestring_list passed to initialize. 
        """
        return self.finalList[finalValueIndex]

    def get_list_of_final_value_tree_indices(self):
        """ 
        Get a list of indices (ints) which specifying the
          tree indices corresponding to each gate string
          in the gatestring_list passed to initialize.

        Returns
        -------
        list of integers
            List of indices with length len(gatestring_list passed to initialize).
            
        Note
        ----
        A reference to the EvalTree's internal
          list is returned, and so the caller should copy
          this list before modifying it.
        """
        return self.finalList #Note: no copy, so caller could modify this!

#    def _initializeBETA(self, gateLabels, gatestring_list):
#        """
#          Experimental alternate tree initialization algorithm.
#          This doesn't currently work.
#        """
#        self.gateLabels = gateLabels
#
#        def repetitions(s):
#            r = _re.compile(r"(.+?)\1+")
#            for match in r.finditer(s):
#                yield (match.group(1), len(match.group(0))/len(match.group(1)))
#
#        #Evaluation dictionary:
#        # keys == gate strings that have been evaluated so far
#        # values == index of gate string (key) within evalTree
#        evalDict = { } 
#
#        #Evaluation tree:
#        # A list of tuples, where each element contains
#        #  information about evaluating a particular gate string:
#        #  (iLeft, iRight, iInFinalList)
#        # and the order of the elements specifies the evaluation order.
#        # In particular, the gateString = evalTree[iLeft] + evalTree[iRight]
#        #  and iInFinalList is the index of this gatestring in the gatestring_list
#        # passed to this function, or -1 if it is not in the list.
#        del self[:] #clear self (a list)
#
#        #Final Index List
#        # A list of integers whose i-th element is the index into evalTree
#        #  corresponding to the i-th gatestring in gatestring_list.
#        finalIndxList = [ None ] * len(gatestring_list)
#
#        #Single gate (or zero-gate) computations are assumed to be atomic, and be computed independently.
#        #  These labels serve as the initial values, and each gate string is assumed to be a tuple of gate labels.
#        singleGateLabels = []
#        for gateLabel in self.gateLabels:
#            if gateLabel == "": #special case of empty label == no gate
#                evalDict[ () ] = len(self)
#            else:
#                evalDict[ (gateLabel,) ] = len(self)
#                singleGateLabels.append(gateLabel)
#            self.append( (None,None,-1) ) #iLeft = iRight = None for always-evaluated zero string
#
#        #Collect list of what sub-strings get repeated a lot
#        repDict = {}
#        for (k,gateString) in enumerate(gatestring_list):
#            #print "String %d (len %d): " % (k,len(gateString)),
#            for repStr,repCnt in repetitions( gateString.to_pythonstr(singleGateLabels) ):
#                repGateStr = _gs.GateString.from_pythonstr(repStr,singleGateLabels)
#                if repDict.has_key(repGateStr):
#                    if repCnt not in repDict[repGateStr][0]:
#                        repDict[repGateStr][0].append(repCnt)
#                        repDict[repGateStr][1].append(1)
#                    else:
#                        indx = repDict[repGateStr][0].index(repCnt)
#                        repDict[repGateStr][1][indx] += 1
#                else:
#                    repDict[repGateStr] = [ [repCnt],[1] ] #list of unique rep counts, list of multiplicities
#                #print "%s^%d" % (str(repGateStr),repCnt),
#            #print ""
#        for repGateStr,repCntList in repDict.iteritems():
#            print repGateStr, ":", repCntList
#
#        self.finalList = []
#        self.myFinalToParentFinalMap = [] #this tree has no "children", i.e. has not been created by a 'split'
#        self.subTrees = []

    def num_final_strings(self):
        """ 
        Returns the integer number of "final" gate strings, equal
          to the length of the gatestring_list passed to initialize.
        """         
        return len(self.finalList)

    def generate_gatestring_list(self):
        """ 
        Generate a list of the final gate strings this tree evaluates.

        This method essentially "runs" the tree and follows its
          prescription for sequentailly building up longer strings
          from shorter ones.  The resulting list should always be
          the same as the one passed to initialize(...), and so
          this method may be used as a consistency check.

        Returns
        -------
        list of gate-label-tuples
            A list of the gate strings evaluated by this tree, each
            specified as a tuple of gate labels.
        """
        finalGateStrings = [None]*self.num_final_strings()
        gateStrings = []
        
        #Set initial single- or zero- gate strings at beginning of tree
        for i,gateLabel in enumerate(self.gateLabels):
            if gateLabel == "": gateStrings.append( () ) #special case of empty label
            else: gateStrings.append( (gateLabel,) )
            if self[i][2] >= 0: #if iFinal for an initial string is >= 0
                finalGateStrings[self[i][2]] = gateStrings[-1]
        n = len(self.gateLabels)

        #Build rest of strings
        for i,tup in enumerate(self[n:],start=n):
            iLeft, iRight, iFinal = tup
            gateStrings.append( gateStrings[iLeft] + gateStrings[iRight] )
            if iFinal >= 0: finalGateStrings[iFinal] = gateStrings[-1]
            
        return finalGateStrings

    def split(self, maxSubTreeSize):
        """ 
        Split this tree into sub-tree in order to reduce the
          maximum size of any tree (useful for limiting memory consumption).

        Parameters
        ----------
        maxSubTreeSize : int
            The maximum size (i.e. list length) of each sub-tree.  If the
            original tree is smaller than this size, no splitting will occur.

        Returns
        -------
        None
        """
        if len(self) < maxSubTreeSize: return #Don't split at all if it's unnecessary

        self.subTrees = []
        self.subTreesFinalList = [None]*len(self.finalList)

        #First pass - identify which indices go in which subtree
        need_to_compute = [False]*len(self)
        for idx in self.finalList: 
            need_to_compute[idx] = True #could speed up using numpy arrays

        subTreeSetList = [] #each element of this represents a subtree, and is a set of the indices owned by that subtree
        for i in reversed(range(len(self))):
            if not need_to_compute[i]: continue # move to the last element of evalTree that needs
                                                #  to be computed (i.e. is not in a subTree)
            subTreeIndices = [] # create subtree for uncomputed item
            self._walkSubTree(i,subTreeIndices)
            newTreeSize = len(subTreeIndices)
            newTreeSet = set(subTreeIndices)
            for k in subTreeIndices: need_to_compute[k] = False #mark all the elements of the new tree as computed

            #See if we should merge this single-item-generated tree with another one or make it a new subtree
            highIntersectSize = None; iHighIntersectSize = None
            for k,existingSubTreeSet in enumerate(subTreeSetList):
                if (len(existingSubTreeSet) + newTreeSize) < maxSubTreeSize:
                    intersectionSize = len(newTreeSet.intersection(existingSubTreeSet))
                    if highIntersectSize is None or highIntersectSize < intersectionSize:
                        highIntersectSize = intersectionSize
                        iHighIntersectSize = k
            if iHighIntersectSize is not None: # then we merge the new tree with this existing set
                subTreeSetList[iHighIntersectSize] = subTreeSetList[iHighIntersectSize].union(newTreeSet)
            else: # we create a new subtree
                subTreeSetList.append( newTreeSet ) 

        #Second pass - create subtrees from index sets
        need_to_compute = [False]*len(self)
        for idx in self.finalList: 
            need_to_compute[idx] = True #could speed up using numpy arrays

        for iSubTree,subTreeSet in enumerate(subTreeSetList):
            subTreeIndices = list(subTreeSet)
            subTreeIndices.sort() # so that we can map order here directly as a subTree (no dependency issues)
            mapIndxToSubTreeIndx = { k: ik for ik,k in enumerate(subTreeIndices) }
            subTree = EvalTree()
            for ik,k in enumerate(subTreeIndices):
                (oLeft,oRight,oFinal) = self[k] #original tree indices

                if (oLeft is None) and (oRight is None): #then k-th index of original tree is an initial element <=> self.gateLabels[k]
                    iLeft = iRight = None
                    assert(len(subTree.gateLabels) == len(subTree)) #make sure all gatelabel items come first
                    subTree.gateLabels.append( self.gateLabels[k] )
                else:
                    iLeft  = mapIndxToSubTreeIndx[ oLeft ]
                    iRight = mapIndxToSubTreeIndx[ oRight ]

                if need_to_compute[k]:
                    need_to_compute[k] = False #compute evalTree[k] == final index oFinal here (this really isn't necessary)
                    iFinal = len(subTree.finalList) #the index within subTree.finalList where this item will go
                    subTree.finalList.append(ik) #added in iFinal position
                    subTree.myFinalToParentFinalMap.append(oFinal)
                    self.subTreesFinalList[oFinal] = (iSubTree,iFinal) #tells which subtree and final list position to find final value
                else:
                    iFinal = -1
                    
                subTree.append( (iLeft,iRight,iFinal) )                
            self.subTrees.append( subTree )    

        return

    def is_split(self):
        """ Returns boolean indicating whether tree is split into sub-trees or not. """
        return len(self.subTrees) > 0

    def get_sub_trees(self):
        """ 
        Returns a list of all the sub-trees (also EvalTree instances) of 
          this tree.  If this tree is not split, returns a single-element
          list containing just the tree.
        """
        if self.is_split():
            return self.subTrees
        else:
            return [self] #return self as the only "subTree" when not split

    def _walkSubTree(self,indx,out):
        if indx not in out: out.append(indx)
        (iLeft,iRight,iFinal) = self[indx]
        if iLeft is not None: self._walkSubTree(iLeft,out)
        if iRight is not None: self._walkSubTree(iRight,out)

    def print_analysis(self):
        """ 
        Print a brief analysis of this tree. Used for 
        debugging and assessing tree quality.
        """

        #Analyze tree
        if not self.is_split():
            print "Size of evalTree = %d" % len(self)
            print "Size of gatestring_list = %d" % len(self.finalList)
    
            lastOccurrance = [-1] * len(self)
            nRefs = [-1] * len(self)
            for i,tup in enumerate(self):
                iLeft,iRight,iFinal = tup
                
                if iLeft is not None:
                    nRefs[iLeft] += 1
                    lastOccurrance[iLeft] = i
    
                if iRight is not None:
                    nRefs[iRight] += 1
                    lastOccurrance[iRight] = i
    
            #print "iTree  nRefs lastOcc  iFinal  inUse"
            maxInUse = nInUse = 0            
            for i,tup in enumerate(self):
                nInUse += 1
                for j in range(i):
                    if lastOccurrance[j] == i and self[j][2] == -1: nInUse -= 1
                maxInUse = max(maxInUse,nInUse)
                #print "%d  %d  %d  %d  %d" % (i, nRefs[i], lastOccurrance[i], tup[2], nInUse)
            print "Max in use at once = (smallest tree size for mem) = %d" % maxInUse
            
        else: #tree is split
            print "Tree is split into %d sub-trees" % len(self.subTrees)
            print "Sub-tree lengths = ", list(map(len,self.subTrees)), " (Sum = %d)" % sum(map(len,self.subTrees))
            #print "Final list: ",self.subTreesFinalList
            for i,t in enumerate(self.subTrees):
                print ">> sub-tree %d: " % i
                t.print_analysis()

        
    def get_analysis_plot_infos(self):
        """ 
        Returns debug plot information useful for 
        assessing the quality of a tree.
        """
        
        analysis = {}
        firstIndxSeen = range(len(self))
        lastIndxSeen = range(len(self))
        subTreeSize = [-1]*len(self)

        xs = []; ys = []
        for i in range(len(self)):
            subTree = []
            self._walkSubTree(i,subTree)
            subTreeSize[i] = len(subTree)
            ys.extend( [i]*len(subTree) + [None] )
            xs.extend( list(sorted(subTree) + [None]) )

            for k,t in enumerate(self):
                (iLeft,iRight,iFinal) = t
                if i in (iLeft,iRight):
                    lastIndxSeen[i] = k

        analysis['SubtreeUsagePlot'] = { 'xs': xs, 'ys': ys, 'title': "Indices used by the subtree rooted at each index",
                                                'xlabel': "Indices used", 'ylabel': 'Subtree root index' }
        analysis['SubtreeSizePlot'] = { 'xs': range(len(self)), 'ys': subTreeSize, 'title': "Size of subtree rooted at each index",
                                                'xlabel': "Subtree root index", 'ylabel': 'Subtree size' }

        xs = [];  ys = []
        for i,rng in enumerate(zip(firstIndxSeen,lastIndxSeen)):
            ys.extend( [i,i,None] )
            xs.extend( [rng[0],rng[1],None] )
        analysis['IndexUsageIntervalsPlot'] = { 'xs': xs, 'ys': ys, 'title': "Usage Intervals of each index",
                                                'xlabel': "Index Interval", 'ylabel': 'Index' }

        return analysis