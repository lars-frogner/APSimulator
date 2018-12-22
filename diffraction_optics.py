# -*- coding: utf-8 -*-
from __future__ import division
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from mpl_toolkits.axes_grid1 import make_axes_locatable, axes_size
from incident_light_field import IncidentLightField


def nearest_higher_power_of_2(number):
    return 2**int(np.ceil(np.log2(number)))


class FraunhoferDiffractionOptics:
    '''
    This class can compute the Fraunhofer diffracted field in the imaging plane
    from the light field incident on an aperture. The incident field is represented
    as a sum of plane waves from different directions, and the resulting Fraunhofer
    diffracted field, which is found by Fourier transforming the incident field on
    passing through the aperture, gives the spatial distribution of spectral flux
    in the imagingnplane. Note that Fraunhofer diffraction only gives the perfectly
    focused image.

    The aperture grid coordinates are normalized with wavelength, so the actual spatial
    position of a grid cell is found by multiplying its normalized coordinate with the
    wavelength. Thus the spatial extent and resolution of the grid depends on the relevant
    wavelength. Performing the Fourier transform with such a grid has the advantage of
    producing results with the same angular resolution for each wavelength, meaning that
    the diffracted field can be directly integrated over wavelength without spatial
    interpolation.
    '''
    def __init__(self, aperture_diameter, focal_length, field_of_view_x, field_of_view_y, max_angular_coarseness, wavelengths):

        self.aperture_diameter = aperture_diameter # Diameter of the aperture [m]
        self.focal_length = focal_length # Focal length of the optical system [m]
        self.wavelengths = wavelengths # Array of wavelengths [m]
        self.field_of_view_x = field_of_view_x # Field of view covered by the diffracted field in the x-direction [rad]
        self.field_of_view_y = field_of_view_y # Field of view covered by the diffracted field in the y-direction [ra
        self.max_angular_coarseness = max_angular_coarseness # Maximum angle that an image grid cell is allowed to subtend [rad]

        self.n_wavelengths = len(wavelengths)
        self.max_field_of_view = max(field_of_view_x, field_of_view_y) # The resolution of the aperture grid is decided by the largest FOV

        self.setup_aperture_grid()
        self.setup_image_grid()

        # Compute values for scaling squared Fourier coeefficients in order to get fluxes
        self.flux_scales = (self.wavelengths*(self.normalized_grid_cell_extent**2/self.focal_length))**2

        # Create instance of incident light field class
        self.incident_light_field = IncidentLightField(self.cropped_normalized_coordinates,
                                                       self.cropped_normalized_coordinates,
                                                       self.wavelengths)

    def setup_aperture_grid(self):

        # Compute the required extent of a cell in the aperture grid to achieve the desired field of view
        self.normalized_grid_cell_extent = 1/(2*np.tan(self.max_field_of_view/2))

        # Compute the required number of cells in the aperture grid to achieve the desired angular resolution
        self.n_grid_cells = nearest_higher_power_of_2(1/(self.max_angular_coarseness*self.normalized_grid_cell_extent))

        # The origin of the aperture coordinates is at the center of the grid
        self.normalized_coordinates = np.arange(-self.n_grid_cells//2, self.n_grid_cells//2)*self.normalized_grid_cell_extent

        # Compute number of grid cells required to cover the largest aperture
        max_normalized_aperture_radius = 0.5*self.aperture_diameter/np.min(self.wavelengths)
        self.n_grid_cells_across_aperture = 2*int(np.ceil(max_normalized_aperture_radius/self.normalized_grid_cell_extent))

        print(self.n_grid_cells, self.n_grid_cells_across_aperture)

        # The largest aperture must not exceed the extent of the grid
        assert self.n_grid_cells_across_aperture <= self.n_grid_cells

        # Compute ranges of indices that just cover the aperture
        self.n_pad_grid_cells = (self.n_grid_cells - self.n_grid_cells_across_aperture)//2
        self.aperture_idx_range = (self.n_pad_grid_cells, self.n_pad_grid_cells + self.n_grid_cells_across_aperture)

        # Extract coordinates covering the aperture
        self.cropped_normalized_coordinates = self.normalized_coordinates[self.aperture_idx_range[0]:self.aperture_idx_range[1]]

        # Note that 'xy'-indexing means that x corresponds to the outer dimension of the array
        self.cropped_normalized_x_coordinate_mesh, \
            self.cropped_normalized_y_coordinate_mesh = np.meshgrid(self.cropped_normalized_coordinates,
                                                                    self.cropped_normalized_coordinates, indexing='xy')

    def setup_image_grid(self):

        # Compute the spatial extent of a cell in the image plane grid where the diffracted field lives
        self.image_grid_cell_extent = self.focal_length/(self.n_grid_cells*self.normalized_grid_cell_extent)

        # The image plane coordinates are proportional to the spatial frequencies of the aperture grid
        full_image_coordinates = np.arange(-self.n_grid_cells//2, self.n_grid_cells//2)*self.image_grid_cell_extent

        # Compute corresponding angles with respect to the optical axis
        full_image_angular_coordinates = np.arctan2(full_image_coordinates, self.focal_length)

        # Compute index ranges for the part of the image spanning the field of view.
        # Outside these ranges, sources will have been filtered out from the incident field.
        # They must still be included in the Fourier transform since we want to have square
        # cells in both the aperture and image grids.
        self.image_idx_range_x = np.searchsorted(full_image_angular_coordinates, (-self.field_of_view_x/2, self.field_of_view_x/2))
        self.image_idx_range_y = np.searchsorted(full_image_angular_coordinates, (-self.field_of_view_y/2, self.field_of_view_y/2))

        self.image_x_coordinates = full_image_coordinates[self.image_idx_range_x[0]:self.image_idx_range_x[1]]
        self.image_y_coordinates = full_image_coordinates[self.image_idx_range_x[0]:self.image_idx_range_x[1]]

        self.image_angular_x_coordinates = full_image_angular_coordinates[self.image_idx_range_x[0]:self.image_idx_range_x[1]]
        self.image_angular_y_coordinates = full_image_angular_coordinates[self.image_idx_range_y[0]:self.image_idx_range_y[1]]

    def get_incident_light_field(self):
        return self.incident_light_field

    def set_incident_field_values(self, field_values):
        self.incident_light_field.set(field_values)

    def modulate_incident_light_field(self, modulation):
        self.incident_light_field.modulate(modulation)

    def get_aperture_diameter(self):
        return self.aperture_diameter

    def get_n_aperture_grid_cells(self):
        return self.n_grid_cells_across_aperture

    def get_normalized_aperture_grid_cell_extent(self):
        return self.normalized_grid_cell_extent

    def add_point_sources(self, polar_angles, azimuth_angles, incident_spectral_fluxes):
        self.incident_light_field.add_point_sources(polar_angles, azimuth_angles,
                                                    incident_spectral_fluxes,
                                                    self.field_of_view_x, self.field_of_view_y)

    def add_extended_source(self, angular_x_coordinates, angular_y_coordinates, incident_spectral_fluxes):
        self.incident_light_field.add_extended_source(angular_x_coordinates, angular_y_coordinates,
                                                      incident_spectral_fluxes,
                                                      self.field_of_view_x, self.field_of_view_y)

    def apply_transmission_mask(self, transmission_mask_function):
        '''
        Masks the incident light field with a boolean function of the spatial aperture coordinates.
        This allows for the aperture to take on arbitrary shapes within its diameter. There will
        be one mask per wavelength, since the number of grid cells covered by the aperture in
        normalized coordinates depends on the wavelength.

        Arguments: Function taking two 3D arrays corresponding to spatial x- and y-meshes for each
                   wavelength. The function must return a boolean array of the same shape with False
                   for every grid cell where the incident field should be set to zero.
        '''
        assert callable(transmission_mask_function)

        # Compute the spatial coordinates of the aperture grid for each wavelength
        x_coordinate_meshes = np.multiply.outer(self.wavelengths, self.cropped_normalized_x_coordinate_mesh)
        y_coordinate_meshes = np.multiply.outer(self.wavelengths, self.cropped_normalized_y_coordinate_mesh)

        self.incident_light_field.apply_transmission_mask(transmission_mask_function(x_coordinate_meshes, y_coordinate_meshes))

    def compute_image_fluxes(self, field_stage='modulated'):
        '''
        Performs the Fourier transformation of the incident field and subsequent scaling that produces
        the flux distribution focused in the image plane.
        '''

        # Since the incident field only just covers the aperture diameter, it must be padded with zeros
        # at the edges to produce the desired angular resolution in the diffracted image
        field_values = np.pad(self.incident_light_field.get(field_stage),
                              ((0, 0),
                               (self.n_pad_grid_cells, self.n_pad_grid_cells),
                               (self.n_pad_grid_cells, self.n_pad_grid_cells)),
                              'constant')

        # Perform the 2D spatial Fourier transform for each wavelength and shift the result to put the
        # origin of the image plane coordinates in the center
        fourier_coefficients = np.fft.fftshift(np.fft.fft2(field_values, axes=(1, 2)), axes=(1, 2))

        # Trim the image to only include the specified field of view
        trimmed_fourier_coefficients = fourier_coefficients[:, self.image_idx_range_y[0]:self.image_idx_range_y[1],
                                                               self.image_idx_range_x[0]:self.image_idx_range_x[1]]

        # Square the Fourier coefficients and multiply with a wavelength-dependent scale that ensures energy conservation
        image_fluxes = (trimmed_fourier_coefficients*np.conj(trimmed_fourier_coefficients)).real*self.flux_scales[:, np.newaxis, np.newaxis]

        return image_fluxes

    def save(self, output_path, compressed=False):

        self.incident_light_field.save(output_path, compressed=compressed)

        if compressed:
            np.savez_compressed(output_path,
                                aperture_diameter=self.aperture_diameter,
                                focal_length=self.focal_length,
                                field_of_view_x=self.field_of_view_x,
                                field_of_view_y=self.field_of_view_y,
                                max_angular_coarseness=self.max_angular_coarseness)
        else:
            np.savez(output_path,
                     aperture_diameter=self.aperture_diameter,
                     focal_length=self.focal_length,
                     field_of_view_x=self.field_of_view_x,
                     field_of_view_y=self.field_of_view_y,
                     max_angular_coarseness=self.max_angular_coarseness)

    def visualize_image(self, approximate_wavelength, field_stage='modulated', use_amplitude=False, verify_energy_conservation=False, output_path=None):
        '''
        Plots the given image plane flux distribution.
        '''

        # Find index of closest wavelength
        wavelength_idx = np.argmin(np.abs(self.wavelengths - approximate_wavelength))
        wavelength = self.wavelengths[wavelength_idx]

        image_fluxes = self.compute_image_fluxes(field_stage=field_stage)
        monochromatic_image_fluxes = image_fluxes[wavelength_idx, :, :]

        arcsec_from_radian = 206264.806
        angular_extent = np.array([self.image_angular_x_coordinates[0], self.image_angular_x_coordinates[-1],
                                   self.image_angular_y_coordinates[0], self.image_angular_y_coordinates[-1]])*arcsec_from_radian

        print('Rayleigh limit: {:g}\"'.format(1.22*wavelength/self.aperture_diameter*arcsec_from_radian))

        if verify_energy_conservation:
            monochromatic_incident_field = self.incident_light_field.get(field_stage)[wavelength_idx, :, :]
            incident_spectral_power = np.sum((monochromatic_incident_field*np.conj(monochromatic_incident_field)).real)\
                                      *(self.normalized_grid_cell_extent*wavelength)**2
            diffracted_spectral_power = np.sum(monochromatic_image_fluxes)*(self.image_grid_cell_extent**2)
            print('Incident spectral power: {:g} W/m\nDiffracted spectral power: {:g} W/m\nRelative energy loss: {:g} %'
                  .format(incident_spectral_power, diffracted_spectral_power, 100*(1 - diffracted_spectral_power/incident_spectral_power)))

        fig, ax = plt.subplots()

        image = ax.imshow(np.sqrt(monochromatic_image_fluxes) if use_amplitude else monochromatic_image_fluxes,
                          origin='lower',
                          interpolation='none',
                          cmap=plt.get_cmap('gray'),
                          extent=angular_extent)
        ax.set_xlabel(r'$\alpha_x$ [arcsec]')
        ax.set_ylabel(r'$\alpha_y$ [arcsec]')
        ax.set_title(r'Image fluxes ($\lambda = {:.1f}$ nm)'.format(wavelength*1e9))

        # Add colorbars
        width = axes_size.AxesY(ax, aspect=0.05)
        pad = axes_size.Fraction(0.4, width)
        divider = make_axes_locatable(ax)
        cax = divider.append_axes('right', size=width, pad=pad)
        fig.colorbar(image, cax=cax, label='Flux [W/m^2/m]')

        plt.tight_layout()

        if output_path is None:
            plt.show()
        else:
            plt.savefig(output_path)

    def animate_image(self, phase_screen, time_step_scale, duration, approximate_wavelength, accumulate=False, savename=False):

        time_step = time_step_scale*phase_screen.coherence_time
        n_time_steps = int(np.ceil(duration/time_step)) + 1

        # Find index of closest wavelength
        wavelength_idx = np.argmin(np.abs(self.wavelengths - approximate_wavelength))
        wavelength = self.wavelengths[wavelength_idx]

        self.incident_light_field.modulate(phase_screen.compute_perturbation_field())

        monochromatic_image_fluxes = self.compute_image_fluxes()[wavelength_idx, :, :]

        vmin = np.min(monochromatic_image_fluxes)
        vmax = np.max(monochromatic_image_fluxes)

        self.integrated_image_fluxes = np.zeros(monochromatic_image_fluxes.shape)

        arcsec_from_radian = 206264.806
        angular_extent = np.array([self.image_angular_x_coordinates[0], self.image_angular_x_coordinates[-1],
                                   self.image_angular_y_coordinates[0], self.image_angular_y_coordinates[-1]])*arcsec_from_radian

        title = ''

        figheight = 5
        aspect = 1.3

        fig = plt.figure(figsize=(aspect*figheight, figheight))
        ax = fig.add_subplot(111)

        ax.set_xlabel(r'$x$ [m]')
        ax.set_ylabel(r'$y$ [m]')
        ax.set_title('{}'.format(title))

        im = ax.imshow(monochromatic_image_fluxes,
                       extent=angular_extent,
                       vmin=vmin, vmax=vmax,
                       origin='lower',
                       aspect='auto',
                       animated=True,
                       interpolation='none',
                       cmap=plt.get_cmap('gray'))

        xleft, xright = ax.get_xlim()
        ybottom, ytop = ax.get_ylim()
        ax.set_aspect(abs((xright-xleft)/(ybottom-ytop)))

        width = axes_size.AxesY(ax, aspect=0.05)
        pad = axes_size.Fraction(0.4, width)
        divider = make_axes_locatable(ax)
        cax = divider.append_axes('right', size=width, pad=pad)
        fig.colorbar(im, cax=cax, label='Intensity [W/m^2/m]')

        time_text = ax.text(0.01, 0.99, '', color='white', ha='left', va='top', transform=ax.transAxes)

        plt.tight_layout(pad=1)

        def init():
            return im, time_text

        def update(time_idx):
            print(time_idx)
            phase_screen.move_phase_screen(time_step)
            self.incident_light_field.modulate(phase_screen.compute_perturbation_field())
            monochromatic_image_fluxes = self.compute_image_fluxes()[wavelength_idx, :, :]
            self.integrated_image_fluxes += monochromatic_image_fluxes
            im.set_array(self.integrated_image_fluxes/(time_idx+1) if accumulate else monochromatic_image_fluxes)
            time_text.set_text('time: {:g} s'.format(phase_screen.time))

            return im, time_text

        anim = animation.FuncAnimation(fig, update, init_func=init, blit=True, frames=np.arange(n_time_steps))

        if savename:
            anim.save(savename, writer=animation.FFMpegWriter(fps=30,
                                                              bitrate=3200,
                                                              extra_args=['-vcodec', 'libx264']))
        else:
            plt.show()


def load_fraunhofer_diffraction_optics(input_path):

    incident_light_field = load_incident_light_field(input_path)

    # Add extension if missing
    final_input_path = input_path + ('.npz' if len(input_path.split('.')) == 1 else '')

    arrays = np.load(final_input_path)
    fraunhofer_diffraction_optics = FraunhoferDiffractionOptics(arrays['aperture_diameter'],
                                                                arrays['focal_length'],
                                                                arrays['field_of_view_x'],
                                                                arrays['field_of_view_y'],
                                                                arrays['max_angular_coarseness'],
                                                                incident_light_field.get_wavelengths())
    fraunhofer_diffraction_optics.set_incident_field_values(incident_light_field.get('pure'))

    return fraunhofer_diffraction_optics


def test():

    from APSimulator import Constants, StarCluster
    from turbulence import TurbulencePhaseScreen, MovingTurbulencePhaseScreen

    n_stars = 1
    FOV_arcsec = 10
    aperture_diameter = 0.15
    secondary_diameter = 0#0.2*aperture_diameter
    spider_wane_width = 0#0.01*aperture_diameter

    def transmission_mask_function(x, y):
        r = np.sqrt(x**2 + y**2)
        return np.logical_and.reduce((r <= aperture_diameter/2,
                                      r >= secondary_diameter/2,
                                      np.abs(x) >= spider_wane_width,
                                      np.abs(y) >= spider_wane_width))

    FOV = FOV_arcsec*Constants.arcsec_to_radian
    target = StarCluster(n_stars, 4, (3000, 30000), (1e-2, 2.0e4), 2e4)
    #target.plot_angular_distribution(FOV_box_halfwidth=FOV_arcsec/2)
    target_info = target.get_target_info()
    polar_angles, azimuth_angles = target.get_spherical_direction_angles()
    incident_spectral_fluxes = np.swapaxes(target_info.get_incident_field_amplitudes()**2, 0, 1)
    max_angular_coarseness = 0.1*Constants.arcsec_to_radian

    optics = FraunhoferDiffractionOptics(aperture_diameter, 0.75, FOV, FOV, max_angular_coarseness, Constants.wavelengths)
    optics.add_point_sources(polar_angles, azimuth_angles, incident_spectral_fluxes)
    optics.apply_transmission_mask(transmission_mask_function)

    turbulence = TurbulencePhaseScreen(0.05, 500e-9, 0, 5, Constants.wavelengths)
    #turbulence = MovingTurbulencePhaseScreen(0.05, 500e-9, 0, 10.0, 5, Constants.wavelengths)
    turbulence.initialize(optics)

    wavelength = 700e-9
    optics.modulate_incident_light_field(turbulence.compute_analytical_modulation_transfer_function())
    print(206264.806*0.98*wavelength/turbulence.get_fried_parameter(wavelength, 0))

    #optics.get_incident_light_field().visualize(500e-9)
    #optics.visualize_image(wavelength, use_amplitude=0)
    #optics.visualize_image(500e-9, use_amplitude=1, field_stage='masked', verify_energy_conservation=True)

    turbulence.plot_structure_function_comparison(500e-9)
    #turbulence.animate(2, 0.2, 500e-9, savename='phase_screen.mp4')

    #optics.animate_image(turbulence, 2, 1, 500e-9, accumulate=True, savename='image2.mp4')

if __name__ == '__main__':
    test()
