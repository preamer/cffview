// A modified version of original vtkFLUENTCFFReader.h
//
// SPDX-FileCopyrightText: Copyright (c) Ken Martin, Will Schroeder, Bill Lorensen
// SPDX-License-Identifier: BSD-3-Clause
//
// Modifications copyright (c) preamer

/**
 * @class   vtkFLUENTCFFReader
 * @brief   reads a dataset in Fluent CFF file format
 *
 * vtkFLUENTCFFReader creates a multiblock dataset containing for each group cell
 * an unstructured grid dataset. It reads .cas.h5 and .dat.h5 files stored in FLUENT
 * CFF format (hdf5).
 *
 * The name of the arrays can be renamed with a more meaningful name that correspond to what Fluent
 * displays. The details for these renamings can be found here:
 * https://ansyshelp.ansys.com/public/account/secured?returnurl=/Views/Secured/corp/v242/en/flu_udf/flu_udf_DataAccessMacros.html
 * https://developer.ansys.com/docs/common-fluids-format-/_data_models_overview.html
 *
 * @par Thanks:
 * Original author : Arthur Piquet
 *
 * This class is based on the vtkFLUENTReader class from Brian W. Dotson &
 * Terry E. Jordan (Department of Energy, National Energy Technology
 * Laboratory) & Douglas McCorkle (Iowa State University)
 *
 * This class reads the HDF5 data in Fluent Format (face type structure)
 * and converts it to VTK Format (cell type structure).
 * This class could be improved for memory performance but the developer
 * will need to rewrite entirely the structure of the class.
 * Some piece of functionality lack in the HDF reading (overset, AMR tree,
 * interface), no file available in order to code/test the structure.
 *
 *
 * @sa
 * vtkFLUENTReader
 */

#pragma once

#include <pybind11/pybind11.h>
#include <string>
#include <memory>
#include <vector>

class vtkFLUENTCFFReader
{
public:
    vtkFLUENTCFFReader();
    ~vtkFLUENTCFFReader();

    pybind11::dict ReadMeshData(const std::string& filename);
    pybind11::object ReadPyVistaMesh(const std::string& filename);

    struct Cell
    {
        int type;
        int zone;
        std::vector<int> faces;
        int parent;
        int child;
        std::vector<int> nodes;
        std::vector<int> nodesOffset;
        std::vector<int> childId;
    };

    struct Face
    {
        int type;
        unsigned int zone;
        std::vector<int> nodes;
        int c0;
        int c1;
        int periodicShadow;
        int parent;
        int child;
        int interfaceFaceParent;
        int interfaceFaceChild;
        int ncgParent;
        int ncgChild;
    };

    /**
     * Enumerate
     */
    enum DataState
    {
        NOT_LOADED = 0,
        AVAILABLE = 1,
        LOADED = 2,
        ERROR = 3
    };

    //@{
    /**
     * Open the HDF5 file structure
     */
    virtual bool OpenCaseFile(const std::string& filename);
    virtual DataState OpenDataFile(const std::string& filename);
    //@}

    /**
     * Retrieve the number of cell zones
     */
    virtual void GetNumberOfCellZones();

    /**
     * Reads necessary information from the .cas file
     */
    virtual void ParseCaseFile();

    /**
     * Get the dimension of the file (2D/3D)
     */
    virtual int GetDimension();

    //@{
    /**
     * Get the total number of nodes/cells/faces
     */
    virtual void GetNodesGlobal();
    virtual void GetCellsGlobal();
    virtual void GetFacesGlobal();
    //@}

    /**
     * Get the size and index of node per zone
     */
    virtual void GetNodes();

    /**
     * Get the topology of cell per zone
     */
    virtual void GetCells();

    /**
     * Get the topology of face per zone
     */
    virtual void GetFaces();

    /**
     * Get the tree (AMR) cell topology
     */
    virtual void GetCellTree();

    /**
     * Get the tree (AMR) face topology
     */
    virtual void GetFaceTree();

    /**
     * Get the interface id of parent faces
     */
    virtual void GetInterfaceFaceParents();

    /**
     * Removes unnecessary faces from the cells
     */
    virtual void CleanCells();

    //@{
    /**
     * Reconstruct and convert the Fluent data format
     * to the VTK format
     */
    virtual void PopulateCellNodes();
    virtual void PopulateCellTree();
    //@}

    //@{
    /**
     * Reconstruct VTK cell topology from Fluent format
     */
    virtual void PopulateTriangleCell(int i);
    virtual void PopulateTetraCell(int i);
    virtual void PopulateQuadCell(int i);
    virtual void PopulateHexahedronCell(int i);
    virtual void PopulatePyramidCell(int i);
    virtual void PopulateWedgeCell(int i);
    virtual void PopulatePolyhedronCell(int i);
    //@}

    /**
     * Read and reconstruct data from .dat.h5 file
     */
     // virtual int GetData();

     /**
      * Pre-read variable name data available for selection
      */
      // virtual int GetMetaData();

      //
      //  Variables
      //
    std::string FileName;
    std::string FileType;
    int Dimension;

    struct vtkInternals;
    std::unique_ptr<vtkInternals> HDFImpl;

    std::vector<double> Points;
    // vtkNew<vtkTriangle> Triangle;
    // vtkNew<vtkTetra> Tetra;
    // vtkNew<vtkQuad> Quad;
    // vtkNew<vtkHexahedron> Hexahedron;
    // vtkNew<vtkPyramid> Pyramid;
    // vtkNew<vtkWedge> Wedge;

    std::vector<Cell> Cells;
    std::vector<Face> Faces;
    std::vector<int> CellZones;

    DataState FileState = DataState::NOT_LOADED;

private:
    vtkFLUENTCFFReader(const vtkFLUENTCFFReader&) = delete;
    void operator=(const vtkFLUENTCFFReader&) = delete;

    struct DataChunk
    {
        std::string variableName;
        int zoneId;
        size_t dim;
        std::vector<double> dataVector;
    };

    std::vector<DataChunk> DataChunks;
    std::vector<std::string> PreReadData;
    int NumberOfArrays = 0;
};
