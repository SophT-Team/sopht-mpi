import pytest
import numpy as np
import sopht_mpi.sopht_mpi_simulator as sps
from sopht.utils.precision import get_real_t
from tests.test_simulator.immersed_body.rigid_body.test_rigid_body_forcing_grids import (
    mock_2d_cylinder,
)
from sopht_mpi.utils import MPIConstruct2D, MPIGhostCommunicator2D


@pytest.mark.mpi(group="MPI_rigid_body_flow_interaction", min_size=2)
@pytest.mark.parametrize("precision", ["single", "double"])
@pytest.mark.parametrize("master_rank", [0, 1])
def test_mpi_rigid_body_flow_interaction(precision, master_rank):
    # Initialize minimal mpi constructs
    grid_size = (16, 16)
    real_t = get_real_t(precision)
    mpi_construct = MPIConstruct2D(
        grid_size_y=grid_size[0],
        grid_size_x=grid_size[1],
        real_t=real_t,
    )
    ghost_size = 2
    mpi_ghost_exchange_communicator = MPIGhostCommunicator2D(
        ghost_size=ghost_size, mpi_construct=mpi_construct
    )

    # Initialize interactor
    cylinder = mock_2d_cylinder()
    forcing_grid_cls = sps.CircularCylinderForcingGrid
    cylinder_flow_interactor = sps.RigidBodyFlowInteractionMPI(
        mpi_construct=mpi_construct,
        mpi_ghost_exchange_communicator=mpi_ghost_exchange_communicator,
        rigid_body=cylinder,
        eul_grid_forcing_field=np.zeros(grid_size),
        eul_grid_velocity_field=np.zeros(grid_size),
        virtual_boundary_stiffness_coeff=1.0,
        virtual_boundary_damping_coeff=1.0,
        dx=1.0,
        grid_dim=2,
        real_t=real_t,
        master_rank=master_rank,
        forcing_grid_cls=forcing_grid_cls,
        num_forcing_points=16,
    )
    rigid_body_dim = 3
    np.testing.assert_allclose(
        cylinder_flow_interactor.body_flow_forces, np.zeros((rigid_body_dim, 1))
    )
    np.testing.assert_allclose(
        cylinder_flow_interactor.body_flow_torques, np.zeros((rigid_body_dim, 1))
    )
    if mpi_construct.rank == master_rank:
        assert isinstance(cylinder_flow_interactor.forcing_grid, forcing_grid_cls)
    else:
        assert isinstance(cylinder_flow_interactor.forcing_grid, sps.EmptyForcingGrid)