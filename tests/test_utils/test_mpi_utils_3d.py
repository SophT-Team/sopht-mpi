import numpy as np
import pytest
from sopht.utils.precision import get_real_t
from sopht.utils.field import VectorField
from sopht_mpi.utils import (
    MPIConstruct3D,
    MPIGhostCommunicator3D,
    MPIFieldCommunicator3D,
    MPILagrangianFieldCommunicator3D,
)
from mpi4py import MPI


@pytest.mark.mpi(group="MPI_utils", min_size=4)
@pytest.mark.parametrize("ghost_size", [1, 2, 3])
@pytest.mark.parametrize("precision", ["single", "double"])
@pytest.mark.parametrize(
    "rank_distribution",
    [(0, 1, 1), (1, 0, 1), (1, 1, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1)],
)
@pytest.mark.parametrize(
    "aspect_ratio",
    [(1, 1, 1), (1, 1, 2), (1, 2, 1), (2, 1, 1), (1, 2, 2), (2, 1, 2), (2, 2, 1)],
)
@pytest.mark.parametrize("master_rank", [0, 1])
def test_mpi_field_gather_scatter(
    ghost_size, precision, rank_distribution, aspect_ratio, master_rank
):
    n_values = 32
    real_t = get_real_t(precision)
    mpi_construct = MPIConstruct3D(
        grid_size_z=n_values * aspect_ratio[0],
        grid_size_y=n_values * aspect_ratio[1],
        grid_size_x=n_values * aspect_ratio[2],
        real_t=real_t,
        rank_distribution=rank_distribution,
    )
    mpi_field_communicator = MPIFieldCommunicator3D(
        ghost_size=ghost_size, mpi_construct=mpi_construct, master_rank=master_rank
    )
    global_scalar_field = np.random.rand(
        mpi_construct.global_grid_size[0],
        mpi_construct.global_grid_size[1],
        mpi_construct.global_grid_size[2],
    ).astype(real_t)
    global_vector_field = np.random.rand(
        mpi_construct.grid_dim,
        mpi_construct.global_grid_size[0],
        mpi_construct.global_grid_size[1],
        mpi_construct.global_grid_size[2],
    ).astype(real_t)
    ref_global_scalar_field = global_scalar_field.copy()
    ref_global_vector_field = global_vector_field.copy()
    local_scalar_field = np.zeros(
        (
            mpi_construct.local_grid_size[0] + 2 * ghost_size,
            mpi_construct.local_grid_size[1] + 2 * ghost_size,
            mpi_construct.local_grid_size[2] + 2 * ghost_size,
        )
    ).astype(real_t)
    local_vector_field = np.zeros(
        (
            mpi_construct.grid_dim,
            mpi_construct.local_grid_size[0] + 2 * ghost_size,
            mpi_construct.local_grid_size[1] + 2 * ghost_size,
            mpi_construct.local_grid_size[2] + 2 * ghost_size,
        )
    ).astype(real_t)
    gather_local_scalar_field = mpi_field_communicator.gather_local_scalar_field
    scatter_global_scalar_field = mpi_field_communicator.scatter_global_scalar_field
    gather_local_vector_field = mpi_field_communicator.gather_local_vector_field
    scatter_global_vector_field = mpi_field_communicator.scatter_global_vector_field
    # scatter global field to other ranks
    scatter_global_scalar_field(local_scalar_field, ref_global_scalar_field)
    scatter_global_vector_field(local_vector_field, ref_global_vector_field)
    # randomise global field after scatter
    global_scalar_field[...] = np.random.rand(
        mpi_construct.global_grid_size[0],
        mpi_construct.global_grid_size[1],
        mpi_construct.global_grid_size[2],
    ).astype(real_t)
    global_vector_field[...] = np.random.rand(
        mpi_construct.grid_dim,
        mpi_construct.global_grid_size[0],
        mpi_construct.global_grid_size[1],
        mpi_construct.global_grid_size[2],
    ).astype(real_t)
    # reconstruct global field from local ranks
    gather_local_scalar_field(global_scalar_field, local_scalar_field)
    gather_local_vector_field(global_vector_field, local_vector_field)
    if mpi_construct.rank == master_rank:
        np.testing.assert_allclose(ref_global_scalar_field, global_scalar_field)
        np.testing.assert_allclose(ref_global_vector_field, global_vector_field)


@pytest.mark.mpi(group="MPI_utils", min_size=4)
@pytest.mark.parametrize("ghost_size", [1, 2, 3])
@pytest.mark.parametrize("precision", ["single", "double"])
@pytest.mark.parametrize(
    "rank_distribution",
    [(0, 1, 1), (1, 0, 1), (1, 1, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1)],
)
@pytest.mark.parametrize(
    "aspect_ratio",
    [(1, 1, 1), (1, 1, 2), (1, 2, 1), (2, 1, 1), (1, 2, 2), (2, 1, 2), (2, 2, 1)],
)
@pytest.mark.parametrize("full_exchange", [True, False])
def test_mpi_ghost_communication(
    ghost_size, precision, rank_distribution, aspect_ratio, full_exchange
):
    n_values = 32
    real_t = get_real_t(precision)
    mpi_construct = MPIConstruct3D(
        grid_size_z=n_values * aspect_ratio[0],
        grid_size_y=n_values * aspect_ratio[1],
        grid_size_x=n_values * aspect_ratio[2],
        periodic_domain=True,
        real_t=real_t,
        rank_distribution=rank_distribution,
    )
    # extra width needed for kernel computation
    mpi_ghost_exchange_communicator = MPIGhostCommunicator3D(
        ghost_size=ghost_size, mpi_construct=mpi_construct, full_exchange=full_exchange
    )
    # Set internal field to manufactured values
    np.random.seed(0)
    local_scalar_field = np.random.rand(
        mpi_construct.local_grid_size[0] + 2 * ghost_size,
        mpi_construct.local_grid_size[1] + 2 * ghost_size,
        mpi_construct.local_grid_size[2] + 2 * ghost_size,
    ).astype(real_t)
    local_vector_field = np.random.rand(
        mpi_construct.grid_dim,
        mpi_construct.local_grid_size[0] + 2 * ghost_size,
        mpi_construct.local_grid_size[1] + 2 * ghost_size,
        mpi_construct.local_grid_size[2] + 2 * ghost_size,
    ).astype(real_t)

    # ghost comm.
    mpi_ghost_exchange_communicator.exchange_scalar_field_init(local_scalar_field)
    mpi_ghost_exchange_communicator.exchange_vector_field_init(local_vector_field)
    mpi_ghost_exchange_communicator.exchange_finalise()

    # check if comm. done rightly!
    # (1) Test faces
    # Comm. along (0, 0, -X)
    np.testing.assert_allclose(
        local_scalar_field[
            ghost_size:-ghost_size, ghost_size:-ghost_size, ghost_size : 2 * ghost_size
        ],
        local_scalar_field[
            ghost_size:-ghost_size,
            ghost_size:-ghost_size,
            -ghost_size : local_scalar_field.shape[2],
        ],
    )
    np.testing.assert_allclose(
        local_vector_field[
            :,
            ghost_size:-ghost_size,
            ghost_size:-ghost_size,
            ghost_size : 2 * ghost_size,
        ],
        local_vector_field[
            :,
            ghost_size:-ghost_size,
            ghost_size:-ghost_size,
            -ghost_size : local_vector_field.shape[3],
        ],
    )
    # Comm. along (0, 0, +X)
    np.testing.assert_allclose(
        local_scalar_field[
            ghost_size:-ghost_size,
            ghost_size:-ghost_size,
            -2 * ghost_size : -ghost_size,
        ],
        local_scalar_field[
            ghost_size:-ghost_size, ghost_size:-ghost_size, 0:ghost_size
        ],
    )
    np.testing.assert_allclose(
        local_vector_field[
            :,
            ghost_size:-ghost_size,
            ghost_size:-ghost_size,
            -2 * ghost_size : -ghost_size,
        ],
        local_vector_field[
            :, ghost_size:-ghost_size, ghost_size:-ghost_size, 0:ghost_size
        ],
    )
    # Comm. along (0, -Y, 0)
    np.testing.assert_allclose(
        local_scalar_field[
            ghost_size:-ghost_size, ghost_size : 2 * ghost_size, ghost_size:-ghost_size
        ],
        local_scalar_field[
            ghost_size:-ghost_size,
            -ghost_size : local_scalar_field.shape[1],
            ghost_size:-ghost_size,
        ],
    )
    np.testing.assert_allclose(
        local_vector_field[
            :,
            ghost_size:-ghost_size,
            ghost_size : 2 * ghost_size,
            ghost_size:-ghost_size,
        ],
        local_vector_field[
            :,
            ghost_size:-ghost_size,
            -ghost_size : local_vector_field.shape[2],
            ghost_size:-ghost_size,
        ],
    )
    # Comm. along (0, +Y, 0)
    np.testing.assert_allclose(
        local_scalar_field[
            ghost_size:-ghost_size,
            -2 * ghost_size : -ghost_size,
            ghost_size:-ghost_size,
        ],
        local_scalar_field[
            ghost_size:-ghost_size, 0:ghost_size, ghost_size:-ghost_size
        ],
    )
    np.testing.assert_allclose(
        local_vector_field[
            :,
            ghost_size:-ghost_size,
            -2 * ghost_size : -ghost_size,
            ghost_size:-ghost_size,
        ],
        local_vector_field[
            :, ghost_size:-ghost_size, 0:ghost_size, ghost_size:-ghost_size
        ],
    )
    # Comm. along (-Z, 0, 0)
    np.testing.assert_allclose(
        local_scalar_field[
            ghost_size : 2 * ghost_size, ghost_size:-ghost_size, ghost_size:-ghost_size
        ],
        local_scalar_field[
            -ghost_size : local_scalar_field.shape[0],
            ghost_size:-ghost_size,
            ghost_size:-ghost_size,
        ],
    )
    np.testing.assert_allclose(
        local_vector_field[
            :,
            ghost_size : 2 * ghost_size,
            ghost_size:-ghost_size,
            ghost_size:-ghost_size,
        ],
        local_vector_field[
            :,
            -ghost_size : local_vector_field.shape[1],
            ghost_size:-ghost_size,
            ghost_size:-ghost_size,
        ],
    )
    # Comm. along (+Z, 0, 0)
    np.testing.assert_allclose(
        local_scalar_field[
            -2 * ghost_size : -ghost_size,
            ghost_size:-ghost_size,
            ghost_size:-ghost_size,
        ],
        local_scalar_field[
            0:ghost_size, ghost_size:-ghost_size, ghost_size:-ghost_size
        ],
    )
    np.testing.assert_allclose(
        local_vector_field[
            :,
            -2 * ghost_size : -ghost_size,
            ghost_size:-ghost_size,
            ghost_size:-ghost_size,
        ],
        local_vector_field[
            :, 0:ghost_size, ghost_size:-ghost_size, ghost_size:-ghost_size
        ],
    )

    if full_exchange:
        # (2) Test edges
        # Comm. along (0, +Y, +X)
        np.testing.assert_allclose(
            local_scalar_field[
                ghost_size:-ghost_size,
                -2 * ghost_size : -ghost_size,
                -2 * ghost_size : -ghost_size,
            ],
            local_scalar_field[ghost_size:-ghost_size, 0:ghost_size, 0:ghost_size],
        )
        np.testing.assert_allclose(
            local_vector_field[
                :,
                ghost_size:-ghost_size,
                -2 * ghost_size : -ghost_size,
                -2 * ghost_size : -ghost_size,
            ],
            local_vector_field[:, ghost_size:-ghost_size, 0:ghost_size, 0:ghost_size],
        )
        # Comm. along (0, -Y, +X)
        np.testing.assert_allclose(
            local_scalar_field[
                ghost_size:-ghost_size,
                ghost_size : 2 * ghost_size,
                -2 * ghost_size : -ghost_size,
            ],
            local_scalar_field[
                ghost_size:-ghost_size,
                -ghost_size : local_scalar_field.shape[1],
                0:ghost_size,
            ],
        )
        np.testing.assert_allclose(
            local_vector_field[
                :,
                ghost_size:-ghost_size,
                ghost_size : 2 * ghost_size,
                -2 * ghost_size : -ghost_size,
            ],
            local_vector_field[
                :,
                ghost_size:-ghost_size,
                -ghost_size : local_vector_field.shape[2],
                0:ghost_size,
            ],
        )
        # Comm. along (0, +Y, -X)
        np.testing.assert_allclose(
            local_scalar_field[
                ghost_size:-ghost_size,
                -2 * ghost_size : -ghost_size,
                ghost_size : 2 * ghost_size,
            ],
            local_scalar_field[
                ghost_size:-ghost_size,
                0:ghost_size,
                -ghost_size : local_scalar_field.shape[2],
            ],
        )
        np.testing.assert_allclose(
            local_vector_field[
                :,
                ghost_size:-ghost_size,
                -2 * ghost_size : -ghost_size,
                ghost_size : 2 * ghost_size,
            ],
            local_vector_field[
                :,
                ghost_size:-ghost_size,
                0:ghost_size,
                -ghost_size : local_vector_field.shape[3],
            ],
        )
        # Comm. along (0, -Y, -X)
        np.testing.assert_allclose(
            local_scalar_field[
                ghost_size:-ghost_size,
                ghost_size : 2 * ghost_size,
                ghost_size : 2 * ghost_size,
            ],
            local_scalar_field[
                ghost_size:-ghost_size,
                -ghost_size : local_scalar_field.shape[1],
                -ghost_size : local_scalar_field.shape[2],
            ],
        )
        np.testing.assert_allclose(
            local_vector_field[
                :,
                ghost_size:-ghost_size,
                ghost_size : 2 * ghost_size,
                ghost_size : 2 * ghost_size,
            ],
            local_vector_field[
                :,
                ghost_size:-ghost_size,
                -ghost_size : local_vector_field.shape[2],
                -ghost_size : local_vector_field.shape[3],
            ],
        )

        # Comm. along (+Z, 0, +X)
        np.testing.assert_allclose(
            local_scalar_field[
                -2 * ghost_size : -ghost_size,
                ghost_size:-ghost_size,
                -2 * ghost_size : -ghost_size,
            ],
            local_scalar_field[0:ghost_size, ghost_size:-ghost_size, 0:ghost_size],
        )
        np.testing.assert_allclose(
            local_vector_field[
                :,
                -2 * ghost_size : -ghost_size,
                ghost_size:-ghost_size,
                -2 * ghost_size : -ghost_size,
            ],
            local_vector_field[:, 0:ghost_size, ghost_size:-ghost_size, 0:ghost_size],
        )
        # Comm. along (-Z, 0, +X)
        np.testing.assert_allclose(
            local_scalar_field[
                ghost_size : 2 * ghost_size,
                ghost_size:-ghost_size,
                -2 * ghost_size : -ghost_size,
            ],
            local_scalar_field[
                -ghost_size : local_scalar_field.shape[0],
                ghost_size:-ghost_size,
                0:ghost_size,
            ],
        )
        np.testing.assert_allclose(
            local_vector_field[
                :,
                ghost_size : 2 * ghost_size,
                ghost_size:-ghost_size,
                -2 * ghost_size : -ghost_size,
            ],
            local_vector_field[
                :,
                -ghost_size : local_vector_field.shape[1],
                ghost_size:-ghost_size,
                0:ghost_size,
            ],
        )
        # Comm. along (+Z, 0, -X)
        np.testing.assert_allclose(
            local_scalar_field[
                -2 * ghost_size : -ghost_size,
                ghost_size:-ghost_size,
                ghost_size : 2 * ghost_size,
            ],
            local_scalar_field[
                0:ghost_size,
                ghost_size:-ghost_size,
                -ghost_size : local_scalar_field.shape[2],
            ],
        )
        np.testing.assert_allclose(
            local_vector_field[
                :,
                -2 * ghost_size : -ghost_size,
                ghost_size:-ghost_size,
                ghost_size : 2 * ghost_size,
            ],
            local_vector_field[
                :,
                0:ghost_size,
                ghost_size:-ghost_size,
                -ghost_size : local_vector_field.shape[3],
            ],
        )
        # Comm. along (-Z, 0, -X)
        np.testing.assert_allclose(
            local_scalar_field[
                ghost_size : 2 * ghost_size,
                ghost_size:-ghost_size,
                ghost_size : 2 * ghost_size,
            ],
            local_scalar_field[
                -ghost_size : local_scalar_field.shape[0],
                ghost_size:-ghost_size,
                -ghost_size : local_scalar_field.shape[2],
            ],
        )
        np.testing.assert_allclose(
            local_vector_field[
                :,
                ghost_size : 2 * ghost_size,
                ghost_size:-ghost_size,
                ghost_size : 2 * ghost_size,
            ],
            local_vector_field[
                :,
                -ghost_size : local_vector_field.shape[1],
                ghost_size:-ghost_size,
                -ghost_size : local_vector_field.shape[3],
            ],
        )

        # Comm. along (+Z, +Y, 0)
        np.testing.assert_allclose(
            local_scalar_field[
                -2 * ghost_size : -ghost_size,
                -2 * ghost_size : -ghost_size,
                ghost_size:-ghost_size,
            ],
            local_scalar_field[0:ghost_size, 0:ghost_size, ghost_size:-ghost_size],
        )
        np.testing.assert_allclose(
            local_vector_field[
                :,
                -2 * ghost_size : -ghost_size,
                -2 * ghost_size : -ghost_size,
                ghost_size:-ghost_size,
            ],
            local_vector_field[:, 0:ghost_size, 0:ghost_size, ghost_size:-ghost_size],
        )
        # Comm. along (-Z, +Y, 0)
        np.testing.assert_allclose(
            local_scalar_field[
                ghost_size : 2 * ghost_size,
                -2 * ghost_size : -ghost_size,
                ghost_size:-ghost_size,
            ],
            local_scalar_field[
                -ghost_size : local_scalar_field.shape[0],
                0:ghost_size,
                ghost_size:-ghost_size,
            ],
        )
        np.testing.assert_allclose(
            local_vector_field[
                :,
                ghost_size : 2 * ghost_size,
                -2 * ghost_size : -ghost_size,
                ghost_size:-ghost_size,
            ],
            local_vector_field[
                :,
                -ghost_size : local_vector_field.shape[1],
                0:ghost_size,
                ghost_size:-ghost_size,
            ],
        )
        # Comm. along (+Z, -Y, 0)
        np.testing.assert_allclose(
            local_scalar_field[
                -2 * ghost_size : -ghost_size,
                ghost_size : 2 * ghost_size,
                ghost_size:-ghost_size,
            ],
            local_scalar_field[
                0:ghost_size,
                -ghost_size : local_scalar_field.shape[1],
                ghost_size:-ghost_size,
            ],
        )
        np.testing.assert_allclose(
            local_vector_field[
                :,
                -2 * ghost_size : -ghost_size,
                ghost_size : 2 * ghost_size,
                ghost_size:-ghost_size,
            ],
            local_vector_field[
                :,
                0:ghost_size,
                -ghost_size : local_vector_field.shape[2],
                ghost_size:-ghost_size,
            ],
        )
        # Comm. along (-Z, -Y, 0)
        np.testing.assert_allclose(
            local_scalar_field[
                ghost_size : 2 * ghost_size,
                ghost_size : 2 * ghost_size,
                ghost_size:-ghost_size,
            ],
            local_scalar_field[
                -ghost_size : local_scalar_field.shape[0],
                -ghost_size : local_scalar_field.shape[1],
                ghost_size:-ghost_size,
            ],
        )
        np.testing.assert_allclose(
            local_vector_field[
                :,
                ghost_size : 2 * ghost_size,
                ghost_size : 2 * ghost_size,
                ghost_size:-ghost_size,
            ],
            local_vector_field[
                :,
                -ghost_size : local_vector_field.shape[1],
                -ghost_size : local_vector_field.shape[2],
                ghost_size:-ghost_size,
            ],
        )

        # (3) Test vertices
        # Comm. along (+Z, +Y, +X)
        np.testing.assert_allclose(
            local_scalar_field[
                -2 * ghost_size : -ghost_size,
                -2 * ghost_size : -ghost_size,
                -2 * ghost_size : -ghost_size,
            ],
            local_scalar_field[0:ghost_size, 0:ghost_size, 0:ghost_size],
        )
        np.testing.assert_allclose(
            local_vector_field[
                :,
                -2 * ghost_size : -ghost_size,
                -2 * ghost_size : -ghost_size,
                -2 * ghost_size : -ghost_size,
            ],
            local_vector_field[:, 0:ghost_size, 0:ghost_size, 0:ghost_size],
        )
        # Comm. along (-Z, +Y, +X)
        np.testing.assert_allclose(
            local_scalar_field[
                ghost_size : 2 * ghost_size,
                -2 * ghost_size : -ghost_size,
                -2 * ghost_size : -ghost_size,
            ],
            local_scalar_field[
                -ghost_size : local_scalar_field.shape[0], 0:ghost_size, 0:ghost_size
            ],
        )
        np.testing.assert_allclose(
            local_vector_field[
                :,
                ghost_size : 2 * ghost_size,
                -2 * ghost_size : -ghost_size,
                -2 * ghost_size : -ghost_size,
            ],
            local_vector_field[
                :, -ghost_size : local_vector_field.shape[1], 0:ghost_size, 0:ghost_size
            ],
        )
        # Comm. along (+Z, -Y, +X)
        np.testing.assert_allclose(
            local_scalar_field[
                -2 * ghost_size : -ghost_size,
                ghost_size : 2 * ghost_size,
                -2 * ghost_size : -ghost_size,
            ],
            local_scalar_field[
                0:ghost_size, -ghost_size : local_scalar_field.shape[1], 0:ghost_size
            ],
        )
        np.testing.assert_allclose(
            local_vector_field[
                :,
                -2 * ghost_size : -ghost_size,
                ghost_size : 2 * ghost_size,
                -2 * ghost_size : -ghost_size,
            ],
            local_vector_field[
                :, 0:ghost_size, -ghost_size : local_vector_field.shape[2], 0:ghost_size
            ],
        )
        # Comm. along (+Z, +Y, -X)
        np.testing.assert_allclose(
            local_scalar_field[
                -2 * ghost_size : -ghost_size,
                -2 * ghost_size : -ghost_size,
                ghost_size : 2 * ghost_size,
            ],
            local_scalar_field[
                0:ghost_size, 0:ghost_size, -ghost_size : local_scalar_field.shape[2]
            ],
        )
        np.testing.assert_allclose(
            local_vector_field[
                :,
                -2 * ghost_size : -ghost_size,
                -2 * ghost_size : -ghost_size,
                ghost_size : 2 * ghost_size,
            ],
            local_vector_field[
                :, 0:ghost_size, 0:ghost_size, -ghost_size : local_vector_field.shape[3]
            ],
        )
        # Comm. along (-Z, -Y, +X)
        np.testing.assert_allclose(
            local_scalar_field[
                ghost_size : 2 * ghost_size,
                ghost_size : 2 * ghost_size,
                -2 * ghost_size : -ghost_size,
            ],
            local_scalar_field[
                -ghost_size : local_scalar_field.shape[0],
                -ghost_size : local_scalar_field.shape[1],
                0:ghost_size,
            ],
        )
        np.testing.assert_allclose(
            local_vector_field[
                :,
                ghost_size : 2 * ghost_size,
                ghost_size : 2 * ghost_size,
                -2 * ghost_size : -ghost_size,
            ],
            local_vector_field[
                :,
                -ghost_size : local_vector_field.shape[1],
                -ghost_size : local_vector_field.shape[2],
                0:ghost_size,
            ],
        )
        # Comm. along (-Z, +Y, -X)
        np.testing.assert_allclose(
            local_scalar_field[
                ghost_size : 2 * ghost_size,
                -2 * ghost_size : -ghost_size,
                ghost_size : 2 * ghost_size,
            ],
            local_scalar_field[
                -ghost_size : local_scalar_field.shape[0],
                0:ghost_size,
                -ghost_size : local_scalar_field.shape[2],
            ],
        )
        np.testing.assert_allclose(
            local_vector_field[
                :,
                ghost_size : 2 * ghost_size,
                -2 * ghost_size : -ghost_size,
                ghost_size : 2 * ghost_size,
            ],
            local_vector_field[
                :,
                -ghost_size : local_vector_field.shape[1],
                0:ghost_size,
                -ghost_size : local_vector_field.shape[3],
            ],
        )
        # Comm. along (+Z, -Y, -X)
        np.testing.assert_allclose(
            local_scalar_field[
                -2 * ghost_size : -ghost_size,
                ghost_size : 2 * ghost_size,
                ghost_size : 2 * ghost_size,
            ],
            local_scalar_field[
                0:ghost_size,
                -ghost_size : local_scalar_field.shape[1],
                -ghost_size : local_scalar_field.shape[2],
            ],
        )
        np.testing.assert_allclose(
            local_vector_field[
                :,
                -2 * ghost_size : -ghost_size,
                ghost_size : 2 * ghost_size,
                ghost_size : 2 * ghost_size,
            ],
            local_vector_field[
                :,
                0:ghost_size,
                -ghost_size : local_vector_field.shape[2],
                -ghost_size : local_vector_field.shape[3],
            ],
        )
        # Comm. along (-Z, -Y, -X)
        np.testing.assert_allclose(
            local_scalar_field[
                ghost_size : 2 * ghost_size,
                ghost_size : 2 * ghost_size,
                ghost_size : 2 * ghost_size,
            ],
            local_scalar_field[
                -ghost_size : local_scalar_field.shape[0],
                -ghost_size : local_scalar_field.shape[1],
                -ghost_size : local_scalar_field.shape[2],
            ],
        )
        np.testing.assert_allclose(
            local_vector_field[
                :,
                ghost_size : 2 * ghost_size,
                ghost_size : 2 * ghost_size,
                ghost_size : 2 * ghost_size,
            ],
            local_vector_field[
                :,
                -ghost_size : local_vector_field.shape[1],
                -ghost_size : local_vector_field.shape[2],
                -ghost_size : local_vector_field.shape[3],
            ],
        )
