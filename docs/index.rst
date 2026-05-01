CheMPAS-A
=========

CheMPAS-A (Chemistry for MPAS - Atmosphere) is an ACOM integration pilot that
couples MUSICA/MICM atmospheric chemistry to MPAS-Atmosphere on its native
unstructured Voronoi mesh, developed as part of the NSF CSSI project QUACS
(Quick Updates to Aerosol and Chemistry Systems for Next Generation Multi-Scale
Models). This is CheMPAS-A 26.04, a pre-release currently in beta testing,
based on MPAS-Model v8.3.1.

**Source:** `github.com/NCAR/CheMPAS-A <https://github.com/NCAR/CheMPAS-A>`_

.. note::

   The official CheMPAS-A release is targeted for late August 2026 and
   will be delivered through the upstream
   `MPAS-Dev/MPAS-Model <https://github.com/MPAS-Dev/MPAS-Model>`_
   repository. The repository linked above is the development and
   prototyping ground; mature pieces are contributed upstream as
   focused pull requests.

CheMPAS-A serves as a rapid-prototyping ground for the chemistry coupling:
runtime tracer allocation, MUSICA/MICM state transfer, TUV-x photolysis,
and idealized chemistry test cases.

CheMPAS-A uses calendar versioning (YY.MM), tracked independently from the
MPAS base model version. This documentation includes an MPAS-Atmosphere
User's Guide adapted from the MPAS v8.3.1 release with CheMPAS-specific
chemistry chapters and namelist entries; a CheMPAS tutorial and developer
notes; and a lightly edited port of the MPAS-Atmosphere Technical
Description from the v8 NCAR Technical Note draft for the dynamical core,
equations, and spatial discretization.

.. admonition:: Under construction
   :class: warning

   These docs are an active port and are not yet feature-complete. In
   particular, figures from the MPAS-Atmosphere User's Guide and Technical
   Description still need to be regenerated — placeholders of the form
   ``**[Figure N.M: caption. To be added next session.]**`` mark the
   intended location of each figure in the Technical Description, and
   figure references in the User's Guide (e.g., Figure 9.1, the vertical
   grid schematics in Appendix C) currently render without their source
   images.

.. seealso::

   `MUSICA documentation <https://musica.readthedocs.io/>`_ —
   **MUSICA** (Multi-Scale Infrastructure for Chemistry and Aerosols):
   the project umbrella, MUSICA-Fortran build instructions, and
   overall chemistry-coupling guidance.

   `MICM documentation <https://micm.readthedocs.io/>`_ —
   **MICM** (Model-Independent Chemistry Module): the chemistry
   solver. Covers mechanism authoring (YAML configs), solver families
   (Rosenbrock, Backward Euler, etc.), rate-constant forms, and
   tolerance / sub-stepping controls.

   `TUV-x documentation <https://tuv-x.readthedocs.io/>`_ —
   **TUV-x** (Tropospheric Ultraviolet and Visible, eXtended): the
   photolysis solver. Covers wavelength grids, cross sections and
   quantum yields, cloud radiator inputs, and the JSON configuration
   format.

   CheMPAS-A is a downstream consumer of all three; the runtime
   species list, rate constants, and photolysis rates come from the
   MICM and TUV-x configurations loaded at startup.

**Contributors:** David Fillmore (NCAR ACOM), Gabriele Pfister (NCAR ACOM),
Avelino Arellano (University of Arizona); Mary Barth (NCAR ACOM),
Matt Dawson (Cohere), Michael Duda (NCAR MMM), Jiwon Gim (NCAR ACOM),
Rajesh Kumar (NCAR RAL), Forrest Lacey (NCAR RAL), Scott Meech (NCAR RAL),
Kyle Shores (NCAR ACOM), Katherine Thayer-Calder (NCAR CGD),
Victor Weeks (NCAR RAL).

**Funding.** This work is supported by the U.S. National Science Foundation
through the Cyberinfrastructure for Sustained Scientific Innovation (CSSI)
program, project *QUACS: Quick Updates to Aerosol and Chemistry Systems for
Next Generation Multi-Scale Models* (PI: Avelino Arellano, University of
Arizona).

.. toctree::
   :maxdepth: 3

   users-guide/index
   tutorial/index
   technical-description/index
